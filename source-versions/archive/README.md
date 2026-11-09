# Source archive transfer

These 18 numbered text files contain the complete ZIP archive, base64-encoded in sorted order to transfer its exact bytes through the connected GitHub integration.

To reassemble on Linux:

```bash
cat source-versions/archive/chunks/part-*.b64 | tr -d '\n' | base64 --decode > EglantinePS5-All-Sources-Newest-to-Oldest.zip
echo '2e466920a9169b04bcb9d4488ef375e0c678ca1c55e3b0ffd3145b8884fae3bd  EglantinePS5-All-Sources-Newest-to-Oldest.zip' | sha256sum -c -
unzip -q EglantinePS5-All-Sources-Newest-to-Oldest.zip
```

The resulting ZIP has 964 files in one root folder, ordered newest to oldest. It contains the source changes provided by the user; the upstream frontend/core checkouts are external. The source expansion workflow extracts these files into browsable repository directories.
