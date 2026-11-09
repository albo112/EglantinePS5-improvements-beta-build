# Public release, Test3 and Test4-A comparison

> **Handoff snapshot:** source and host evidence below are real. Native build, final checks and packaging are explicitly labelled by their available receipts. No Test4-A PS5 run is claimed.

| Property | Public v1.219.020 | Supplied Zelda Test3 | Test4-A snapshot |
| --- | --- | --- | --- |
| Original package SHA-256 | `8209561dc5e9328e92cc8668a084e4f4e37b26e30df5c9d614a28a90470d4ae7` | `55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7` | See adjacent verification receipt |
| Extracted files | 69 | 71 | See adjacent verification receipt |
| User-observed FPS | 15–19, supplied by user | 30–58, supplied by user | Not measured |
| Controlled matched benchmark | None provided | None provided | Not performed |
| New supplied crash logs | No verified public-release trial in Logs3–5 | Eight crashes / nine launches; symbols support Test3 | No PS5 trial |
| Mesh configuration | Not inferred from binary alone | All observed profiles say 0 but presence-based source still skips mesh work | Literal 0 parsing corrected and host-tested; visual result pending |
| Profile comparison | No matched trial | Supplied crash sessions use Faster; `LONE=0` may omit foliage | Unchanged 49-key Prettier is default. Faster is retained only as the historical incomplete-graphics baseline. |
| Compiler OOM crash boundary | Not inferred without matching symbols/source | Six identical null dynamic-array writes | Checked optimization abort implemented; 8 initial real-NIR host cases plus 24 caller cases pass. Native build passed; console validation remains unperformed. |
| Cached textures after allocation refusal | No matched runtime evidence | Sparse-image fallback warnings under pressure | Scoped cleanup/backoff/retry implemented; 16 simulated-allocation host cases pass; hardware result pending |
| Test3 upload/range/shader/display guards | Not inferred | Reconstructed and retained | Supplied checks pass; final receipt shown in validation report |
| Targeted diagnostics | Not inferred | Verbose draw-failure Debug output | Bounded cumulative warnings, heap-failure snapshot, fault instruction bytes and boot marker; host checked |
| Remote dashboard | Not assessed | Not required | Excluded; reserved for Test4-B |

The user-observed FPS ranges are useful motivation, not a measured regression guarantee. Logged Test3 medians vary from 1.1 to 59.366 FPS by session; scenes, duration, Debug logging and memory pressure differ. The fastest short sample is not representative of longer demanding gameplay, and the longest observed final session ends in a crash after approximately 629 s.

Test3's omitted mesh work is a concrete confounder. Restoring valid rendering can reduce numeric FPS while improving correctness. The goal is to retain legitimate Test3 optimizations, not reproduce a high counter by dropping essential geometry. No Test4-A change is certified solely because its logs become quieter.

Acceptance requires the same route/save/cache/output/profile comparison, correct vegetation/textures, no new pipeline/image errors, better sustained headroom and measured duration/FPS. If a change fails those checks, revise or revert that isolated change rather than adding unrelated tuning.
