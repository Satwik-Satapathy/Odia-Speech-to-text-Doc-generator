# Quality evaluation

Place golden audio files under `quality/audio/` and run the batch workflow against them. Store the returned transcript beside each sample, then compare it with `reference_transcript` using `backend.app.quality.word_error_rate` and `character_error_rate`.

The samples intentionally cover clean speech, Odia-English code mixing, names, and numbers. Add noisy, accented, and multi-speaker recordings before changing the Saaras model or normalization rules.
