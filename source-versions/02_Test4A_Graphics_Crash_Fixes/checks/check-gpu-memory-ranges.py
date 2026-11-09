#!/usr/bin/env python3
"""Compile exact copied GPU-memory functions against checked fake dependencies.

Reads the selected source tree, applies the supplied patch only to scratch copies,
and checks patch applicability against the original without changing it.
"""
import argparse, hashlib, json, pathlib, shutil, subprocess

def run(argv, **kwargs):
    return subprocess.run(argv, text=True, capture_output=True, **kwargs)

def body(source, needle):
    pos = source.index(needle)
    start = source.rfind('\n', 0, pos) + 1
    opening = source.index('{', pos)
    depth = 0
    for end in range(opening, len(source)):
        if source[end] == '{': depth += 1
        elif source[end] == '}':
            depth -= 1
            if depth == 0: return source[start:end + 1]
    raise AssertionError(needle)

FUNCTIONS = [
    'MemoryManager::GetEntry(', 'MemoryManager::MemoryOperation(',
    'MemoryManager::ReadBlockImpl(', 'MemoryManager::WriteBlockImpl(',
    'MemoryManager::WriteBlockCached(', 'MemoryManager::WriteWordsCached(',
    'MemoryManager::FlushRegion(', 'MemoryManager::IsMemoryDirty(',
    'MemoryManager::MaxContinuousRange(', 'MemoryManager::MaxContinuousRangeUncached(',
    'MemoryManager::InvalidateRegion(', 'MemoryManager::IsGranularRange(',
    'MemoryManager::IsContinuousRange(', 'MemoryManager::IsFullyMappedRange(',
    'MemoryManager::GetSubmappedRangeImpl(',
]

PREAMBLE = r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
using u8=std::uint8_t; using u32=std::uint32_t; using u64=std::uint64_t;
using GPUVAddr=u64; using DAddr=u64;
namespace Core { constexpr size_t DEVICE_PAGESIZE=4096, DEVICE_PAGEMASK=4095; }
namespace VideoCommon { enum class CacheType { None, All }; }
namespace boost::container { template<class T,size_t N> using small_vector=std::vector<T>; }
static size_t table_reads=0, oob_attempts=0, assertions=0;
static void check(bool condition,const char* name) {
    ++assertions; if(!condition) throw std::runtime_error(name);
}
template<class T> struct CheckedTable {
    size_t limit; std::unordered_map<size_t,T> values;
    explicit CheckedTable(size_t n):limit(n) {}
    void validate(size_t i) const { if(i>=limit) { ++oob_attempts; throw std::out_of_range("page table index"); } }
    T operator[](size_t i) const { validate(i); ++table_reads; auto p=values.find(i); return p==values.end()?T{}:p->second; }
    T& operator[](size_t i) { validate(i); return values[i]; }
};
struct FakeMemory {
    std::vector<u8> bytes=std::vector<u8>(1<<20);
    template<class T> T* GetPointer(DAddr a) { return a<bytes.size()?reinterpret_cast<T*>(bytes.data()+a):nullptr; }
    void ReadBlockUnsafe(DAddr a,void* d,size_t n) { check(a<=bytes.size() && n<=bytes.size()-a,"host read bounds"); std::memcpy(d,bytes.data()+a,n); }
    void WriteBlockUnsafe(DAddr a,const void* s,size_t n) { check(a<=bytes.size() && n<=bytes.size()-a,"host write bounds"); std::memcpy(bytes.data()+a,s,n); }
};
struct FakeRasterizer {
    size_t flushes=0, invalidations=0, preparations=0, dirty_checks=0; bool dirty=false;
    void FlushRegion(DAddr,size_t,VideoCommon::CacheType) { ++flushes; }
    void InvalidateRegion(DAddr,size_t,VideoCommon::CacheType) { ++invalidations; }
    void PrepareRegionWrite(DAddr,size_t,VideoCommon::CacheType) { ++preparations; }
    bool MustFlushRegion(DAddr,size_t,VideoCommon::CacheType) { ++dirty_checks; return dirty; }
};
struct FakeAccumulator {
    std::vector<std::pair<GPUVAddr,size_t>> ranges;
    void Add(GPUVAddr a,size_t n) { ranges.emplace_back(a,n); }
};
namespace Tegra {
static size_t sparse_write_calls=0;
std::atomic<u64> g_nx2_sparse_low{u64{1}<<39},g_nx2_sparse_high{u64{1}<<40};
void Nx2BackSparseWrite(GPUVAddr,size_t,const void*) { ++sparse_write_calls; }
class MemoryManager {
public:
    enum class EntryType:u64 { Free=0,Reserved=1,Mapped=2 };
    static constexpr size_t page_bits=12,page_size=4096,page_mask=4095,cpu_page_bits=12;
    static constexpr size_t big_page_bits=16,big_page_size=65536,big_page_mask=65535;
    u64 address_space_size=u64{1}<<40;
    CheckedTable<u64> entries{(u64{1}<<40)/page_size/32},sparse_entries{(u64{1}<<40)/page_size/32},big_entries{(u64{1}<<40)/big_page_size/32};
    CheckedTable<u32> page_table{(u64{1}<<40)/page_size},big_page_table_dev{(u64{1}<<40)/big_page_size};
    bool use_sparse_entries=false;
    std::unordered_set<size_t> continuous_big;
    mutable FakeMemory memory;
    FakeRasterizer rasterizer_value; FakeRasterizer* rasterizer=&rasterizer_value;
    FakeAccumulator accumulator;
    std::atomic<u64> map_serial{1}; size_t unique_identifier;
    MemoryManager():unique_identifier(next_id++) {}
    inline static size_t next_id=1;
    bool IsBigPageContinuous(size_t i) const { check(i<big_page_table_dev.limit,"continuous table index"); return continuous_big.contains(i); }
    void MapSmall(GPUVAddr a,DAddr d,EntryType t=EntryType::Mapped) {
        size_t i=a>>page_bits; auto& e=use_sparse_entries?sparse_entries[i/32]:entries[i/32];
        e=(e&~(u64{3}<<(2*(i%32))))|(static_cast<u64>(t)<<(2*(i%32))); page_table[i]=static_cast<u32>(d>>cpu_page_bits); ++map_serial;
    }
    void MapBig(GPUVAddr a,DAddr d,EntryType t=EntryType::Mapped) {
        size_t i=a>>big_page_bits; auto& e=big_entries[i/32];
        e=(e&~(u64{3}<<(2*(i%32))))|(static_cast<u64>(t)<<(2*(i%32))); big_page_table_dev[i]=static_cast<u32>(d>>cpu_page_bits); continuous_big.insert(i); ++map_serial;
    }
PREDICATES
    EntryType GetEntry(size_t,bool) const;
    template<class M,class R,class U> inline void MemoryOperation(GPUVAddr,size_t,bool,M&&,R&&,U&&) const;
    void ReadBlockImpl(GPUVAddr,void*,size_t,VideoCommon::CacheType,bool) const;
    void WriteBlockImpl(GPUVAddr,const void*,size_t,VideoCommon::CacheType,bool);
    void WriteBlockCached(GPUVAddr,const void*,size_t);
    void WriteWordsCached(GPUVAddr,const u32*,size_t);
    void FlushRegion(GPUVAddr,size_t,VideoCommon::CacheType) const;
    bool IsMemoryDirty(GPUVAddr,size_t,VideoCommon::CacheType) const;
    size_t MaxContinuousRange(GPUVAddr,size_t) const;
    size_t MaxContinuousRangeUncached(GPUVAddr,size_t) const;
    void InvalidateRegion(GPUVAddr,size_t,VideoCommon::CacheType) const;
    bool IsGranularRange(GPUVAddr,size_t) const;
    bool IsContinuousRange(GPUVAddr,size_t) const;
    bool IsFullyMappedRange(GPUVAddr,size_t) const;
    template<bool G> void GetSubmappedRangeImpl(GPUVAddr,size_t,boost::container::small_vector<std::pair<std::conditional_t<G,GPUVAddr,DAddr>,size_t>,32>&) const;
};
// Existing source lambdas have intentionally unused callback parameters.
// Keep the copied functions exact and suppress only that pre-existing warning.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused-parameter"
'''

TESTS = r'''
#pragma clang diagnostic pop
} // namespace Tegra
using Tegra::MemoryManager;
constexpr auto All=VideoCommon::CacheType::All;
static void baseline() {
    MemoryManager m; size_t reproduced=0;
    try { static_cast<void>(m.IsContinuousRange(0x61acd640a0060ea0ULL,4)); } catch(const std::out_of_range&) { ++reproduced; }
    try { static_cast<void>(m.IsMemoryDirty(0x00000e1c8000068bULL,4,All)); } catch(const std::out_of_range&) { ++reproduced; }
    check(reproduced==2,"baseline reproduces both observed invalid addresses");
    std::cout << "{\"baseline_oob_reproductions\":" << reproduced << ",\"table_oob_attempts\":" << oob_attempts << ",\"table_reads\":" << table_reads << "}\n";
}
#ifdef PATCHED_FUNCTIONS
static void fixed() {
    MemoryManager m; const u64 limit=m.address_space_size; const size_t max=std::numeric_limits<size_t>::max();
    const std::array<std::pair<u64,size_t>,9> invalid{{
        {0x61acd640a0060ea0ULL,4},{0x00000e1c8000068bULL,4},{limit,1},{limit+1,8},
        {limit-1,2},{max,1},{max-3,8},{0x1000,max},{0,static_cast<size_t>(limit)+1}}};
    std::array<u8,32> buffer{}; std::array<u32,2> words{0x11223344U,0x55667788U};
    for(const auto& [a,n]:invalid) {
        const auto reads=table_reads; const auto sparse=Tegra::sparse_write_calls; const auto acc=m.accumulator.ranges.size();
        check(!m.IsWithinGPUAddressRange(a,n),"invalid range predicate");
        check(!m.IsContinuousRange(a,n),"invalid continuous false");
        check(!m.IsFullyMappedRange(a,n),"invalid fully mapped false");
        check(!m.IsMemoryDirty(a,n,All),"invalid dirty false");
        check(m.MaxContinuousRange(a,n)==0,"invalid maximum zero");
        check(!m.IsGranularRange(a,n),"invalid granular false");
        m.FlushRegion(a,n,All); m.InvalidateRegion(a,n,All);
        m.WriteBlockImpl(a,words.data(),n,All,false); m.WriteBlockCached(a,words.data(),n);
        std::vector<std::pair<u64,size_t>> sub;
        m.GetSubmappedRangeImpl<true>(a,n,sub); check(sub.empty(),"invalid GPU submaps empty");
        m.GetSubmappedRangeImpl<false>(a,n,sub); check(sub.empty(),"invalid CPU submaps empty");
        if(n<=buffer.size()) {
            buffer.fill(0xa5); m.ReadBlockImpl(a,buffer.data(),n,All,false);
            check(std::all_of(buffer.begin(),buffer.begin()+n,[](u8 v){return v==0;}),"invalid read zero fill");
            check(std::all_of(buffer.begin()+n,buffer.end(),[](u8 v){return v==0xa5;}),"read preserves host suffix");
        }
        check(table_reads==reads,"invalid walkers never access tables");
        check(Tegra::sparse_write_calls==sparse,"invalid writes never sparse-back");
        check(m.accumulator.ranges.size()==acc,"invalid writes never accumulate");
        for(bool big:{false,true}) {
            size_t mapped=0,reserved=0,unmapped=0,amount=0;
            auto yes=[&](size_t,size_t,size_t){++mapped;return false;};
            auto reserve=[&](size_t,size_t,size_t){++reserved;return false;};
            auto no=[&](size_t i,size_t off,size_t count){++unmapped;amount=count;check(i==(a>>(big?16:12)),"callback original page index");check(off==(a&(big?65535:4095)),"callback original page offset");return false;};
            m.MemoryOperation(a,n,big,yes,reserve,no);
            check(mapped==0 && reserved==0 && unmapped==1 && amount==n,"bool invalid callback once");
            mapped=reserved=unmapped=0;
            auto vm=[&](size_t,size_t,size_t){++mapped;};auto vr=[&](size_t,size_t,size_t){++reserved;};auto vu=[&](size_t,size_t,size_t){++unmapped;};
            m.MemoryOperation(a,n,big,vm,vr,vu);
            check(mapped==0 && reserved==0 && unmapped==1,"void invalid callback once");
        }
    }
    for(u64 a:std::array<u64,5>{0,0x1000,limit,0x61acd640a0060ea0ULL,std::numeric_limits<u64>::max()}) {
        size_t callbacks=0;auto cb=[&](size_t,size_t,size_t){++callbacks;}; const auto reads=table_reads;
        m.MemoryOperation(a,0,false,cb,cb,cb);m.MemoryOperation(a,0,true,cb,cb,cb);
        check(callbacks==0 && table_reads==reads,"empty request no callback or lookup");
        check(m.IsContinuousRange(a,0) && m.IsFullyMappedRange(a,0),"empty query semantics");
        check(!m.IsMemoryDirty(a,0,All) && m.MaxContinuousRange(a,0)==0,"empty dirty and maximum");
        buffer.fill(0xa5);m.ReadBlockImpl(a,buffer.data(),0,All,false);check(buffer[0]==0xa5,"empty read untouched");
        auto sparse=Tegra::sparse_write_calls;auto acc=m.accumulator.ranges.size();
        m.WriteBlockImpl(a,words.data(),0,All,false);m.WriteBlockCached(a,words.data(),0);m.WriteWordsCached(a,words.data(),0);
        check(Tegra::sparse_write_calls==sparse && m.accumulator.ranges.size()==acc,"empty writes no side effect");
    }
    for(u64 a:std::array<u64,5>{limit,limit+1,0x61acd640a0060ea0ULL,0x00000e1c8000068bULL,std::numeric_limits<u64>::max()}) {
        auto reads=table_reads;check(m.GetEntry(a,true)==MemoryManager::EntryType::Free,"invalid big entry free");check(m.GetEntry(a,false)==MemoryManager::EntryType::Free,"invalid small entry free");check(table_reads==reads,"invalid entry no lookup");
    }
    check(m.IsWithinGPUAddressRange(0,limit),"whole address space fits");
    check(m.IsWithinGPUAddressRange(limit-1,1),"last byte fits");
    m.MapSmall(0x1000,0x2000);m.MapSmall(0x2000,0x3000);m.MapSmall(0x3000,0x4000);
    m.MapSmall(limit-4096,0x5000);
    check(m.IsContinuousRange(limit-4,4) && m.IsFullyMappedRange(limit-4,4),"range ending at limit valid");
    check(m.IsContinuousRange(0x1000,8192) && m.IsFullyMappedRange(0x1000,8192),"valid nested fallback contiguous");
    check(m.MaxContinuousRange(0x1000,8192)==8192,"valid maximum");check(m.MaxContinuousRange(0x1000,8192)==8192,"cached valid maximum");
    check(m.IsGranularRange(0x1001,4),"valid granular");
    check(!m.IsGranularRange(0x1001,max),"granular overflow rejected");
    std::vector<std::pair<u64,size_t>> sub;m.GetSubmappedRangeImpl<true>(0x1000,8192,sub);check(sub.size()==1 && sub[0]==std::pair<u64,size_t>{0x1000,8192},"valid GPU submaps");
    sub.clear();m.GetSubmappedRangeImpl<false>(0x1000,8192,sub);check(sub.size()==1 && sub[0]==std::pair<u64,size_t>{0x2000,8192},"valid CPU submaps");
    for(size_t i=0;i<8;++i)m.memory.bytes[0x2ffc+i]=static_cast<u8>(i+1);
    buffer.fill(0);m.ReadBlockImpl(0x1ffc,buffer.data(),8,All,false);for(size_t i=0;i<8;++i)check(buffer[i]==i+1,"cross-page valid read");
    m.rasterizer_value.dirty=true;check(m.IsMemoryDirty(0x1000,16,All),"mapped dirty propagates");m.rasterizer_value.dirty=false;
    size_t visited=0;auto stop=[&](size_t,size_t,size_t){++visited;return true;};auto unused=[](size_t,size_t,size_t){return false;};
    m.MemoryOperation(0x1800,8192,false,stop,unused,unused);check(visited==1,"bool callback early stop");
    visited=0;size_t bytes=0;auto count=[&](size_t,size_t,size_t n){++visited;bytes+=n;};auto noop=[](size_t,size_t,size_t){};
    m.MemoryOperation(0x1800,8192,false,count,noop,noop);check(visited==3 && bytes==8192,"void multipage callbacks");
    m.MapSmall(0x4000,0,MemoryManager::EntryType::Reserved);
    check(!m.IsContinuousRange(0x4000,4),"small reserved not continuous");check(m.IsFullyMappedRange(0x4000,4),"existing small reserved fully-mapped semantics preserved");
    buffer.fill(0xa5);m.ReadBlockImpl(0x4000,buffer.data(),4,All,false);check(buffer[0]==0 && buffer[3]==0,"reserved read zero");
    m.MapBig(0x20000,0,MemoryManager::EntryType::Reserved);check(!m.IsFullyMappedRange(0x20000,4),"existing big reserved semantics preserved");
    m.MapBig(0x10000,0x10000);check(m.IsContinuousRange(0x10000,65536),"mapped big-page continuous");check(m.IsGranularRange(0x10000,4),"mapped big granular");
    auto sparse=Tegra::sparse_write_calls;auto acc=m.accumulator.ranges.size();
    m.WriteBlockCached(0x1000,words.data(),8);check(Tegra::sparse_write_calls==sparse+1 && m.accumulator.ranges.size()==acc+1,"valid cached write side effects");check(std::memcmp(m.memory.bytes.data()+0x2000,words.data(),8)==0,"valid cached write bytes");
    sparse=Tegra::sparse_write_calls;acc=m.accumulator.ranges.size();
    m.WriteWordsCached(0x2000,words.data(),2);check(Tegra::sparse_write_calls==sparse+1 && m.accumulator.ranges.size()==acc+2,"valid word accumulator semantics");
    sparse=Tegra::sparse_write_calls;acc=m.accumulator.ranges.size();
    for(u64 a:std::array<u64,3>{limit,limit-1,0x61acd640a0060ea0ULL})m.WriteWordsCached(a,words.data(),2);
    m.WriteWordsCached(0,words.data(),max);m.WriteWordsCached(0,words.data(),static_cast<size_t>(limit/4)+1);
    check(Tegra::sparse_write_calls==sparse && m.accumulator.ranges.size()==acc,"invalid word count/range no side effects");
    check(oob_attempts==0,"fixed code never attempted checked table OOB");
    std::cout << "{\"assertions\":" << assertions << ",\"table_oob_attempts\":" << oob_attempts << ",\"invalid_cases\":" << invalid.size() << ",\"source_functions\":15}\n";
}
#endif
int main(int argc,char** argv) {
    try {
#ifdef PATCHED_FUNCTIONS
        if(argc==2 && std::string(argv[1])=="baseline")baseline();else fixed();
#else
        static_cast<void>(argc);static_cast<void>(argv);baseline();
#endif
    }
    catch(const std::exception& e) { std::cerr<<e.what()<<"\n";return 1; }
}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=pathlib.Path,required=True)
    parser.add_argument('--patch',type=pathlib.Path,default=pathlib.Path(__file__).with_name('0429-gpu-memory-range-guards.patch'))
    parser.add_argument('--applied',action='store_true',help='Validate already-patched source; reverse only in scratch for baseline')
    parser.add_argument('--work-dir',type=pathlib.Path,default=pathlib.Path(__file__).parent/'upstream-audit/range-harness')
    parser.add_argument('--evidence',type=pathlib.Path,default=pathlib.Path(__file__).with_name('upstream-range-guard-evidence.json'))
    args=parser.parse_args();args.work_dir.mkdir(parents=True,exist_ok=True)
    paths=['src/video_core/memory_manager.cpp','src/video_core/memory_manager.h']
    original={p:(args.source/p).read_bytes() for p in paths}
    evidence={'source':str(args.source),'patch':str(args.patch),'source_sha256':{p:hashlib.sha256(v).hexdigest() for p,v in original.items()},'tests':{}}
    direction=['-R'] if args.applied else []
    check_patch=run(['git','-C',str(args.source),'apply',*direction,'--check',str(args.patch.resolve())])
    evidence['actual_source_git_apply_check']={'exit_code':check_patch.returncode,'stderr':check_patch.stderr}
    if check_patch.returncode: raise RuntimeError(check_patch.stderr)
    for variant in ['baseline','patched']:
        directory=args.work_dir/variant;directory.mkdir(exist_ok=True)
        for p,data in original.items():
            dest=directory/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        if (variant=='patched') != args.applied:
            applied=run(['git','apply',*direction,str(args.patch.resolve())],cwd=directory)
            if applied.returncode: raise RuntimeError(applied.stderr)
        cpp=(directory/paths[0]).read_text();header=(directory/paths[1]).read_text()
        needles=['IsWithinGPUAddressRange(GPUVAddr gpu_addr) const']
        if variant=='patched':needles.append('IsWithinGPUAddressRange(GPUVAddr gpu_addr, std::size_t size) const')
        predicates='\n'.join(body(header,n) for n in needles)
        functions=[]
        for needle in FUNCTIONS:
            text=body(cpp,needle)
            if needle=='MemoryManager::MemoryOperation(':text='template <typename FuncMapped, typename FuncReserved, typename FuncUnmapped>\n'+text
            if needle=='MemoryManager::GetSubmappedRangeImpl(':text='template <bool is_gpu_address>\n'+text
            functions.append(text)
        harness=directory/'harness.cpp';harness.write_text(PREAMBLE.replace('PREDICATES',predicates)+'\n'.join(functions)+TESTS)
        binary=directory/'harness'
        command=['clang++-18','-std=c++20','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(harness),'-o',str(binary)]
        if variant=='patched':command.insert(1,'-DPATCHED_FUNCTIONS')
        compiled=run(command)
        evidence['tests'][variant]={'compile_command':command,'compile_exit_code':compiled.returncode,'compile_stderr':compiled.stderr}
        if compiled.returncode:
            args.evidence.write_text(json.dumps(evidence,indent=2));raise RuntimeError(compiled.stderr)
        result=run([str(binary),'baseline' if variant=='baseline' else 'fixed'])
        evidence['tests'][variant].update({'run_exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        if result.returncode:
            args.evidence.write_text(json.dumps(evidence,indent=2));raise RuntimeError(result.stderr)
    evidence['source_unchanged']=all((args.source/p).read_bytes()==data for p,data in original.items())
    evidence['patch_sha256']=hashlib.sha256(args.patch.read_bytes()).hexdigest()
    evidence['warning_note']='Only existing source unused-parameter warnings are suppressed around exact extracted functions; all other Wall/Wextra warnings remain errors.'
    args.evidence.write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':main()
