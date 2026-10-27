# Feedback humanizer integration

The active guarded editor uses adapted Blader Humanizer principles in
editor_prompt.txt; see ../blader-humanizer/README.md for the MIT reference.
The sources and weights below describe the evaluated dedicated model, which
was rejected for academic feedback and is retained only for diagnostics.

Source: https://github.com/sgaofen/humanizer-local-model
Code revision: `7dd4be90cb3acb2e5d18aeea5837f888d2bb2d52`
Model: https://huggingface.co/jialinyyzz/humanizer
Model revision: `2e57b6528a4070c33f3e09ca24e3325a84272f68`

Only the upstream prompt and license/notice are vendored. The diagnostic adapter
uses the pinned prompt verbatim through raw completion, with upstream sampling.
The model and runtime are stored in ignored output/humanizer. This project adds
fact preservation and review-structure guards outside the model. Those checks
cannot prove semantic equivalence or a third-party detector result.

IQ2_XS-QAT size: 3,893,632,896 bytes.
SHA-256: `383e5ca8f1f48ab5f65013adbc1965fa70d1d1afa6c45d932c34b854e38edbb5`.
