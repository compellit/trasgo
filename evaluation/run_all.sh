#!/usr/bin/env bash
# Regenerate the evaluation results in results/ (trasgo must be installed, e.g. pip install -e ..).
# Cotovia results are not regenerated here: they need the external cotovia program
# (see evaluate_cotovia.py).
set -euo pipefail
cd "$(dirname "$0")"

FLAGS="-c -t -b"   # complex codas, thetacism, broad transcription
mkdir -p results/words results/ilenia results/iago

# Isolated words (Banco de Voces): word in column 1, IPA in column 3
for split in dev test; do
    python3 evaluate_words.py "data/banco_de_voces_pronuncia_${split}.csv" \
        --no-header --word-col-index 1 --phon-col-index 3 $FLAGS \
        --progress-every 0 --output-file "results/words/${split}.tsv"
done

# Running text: Ilenia (adjudicated reference) and Iago
python3 evaluate_ilenia.py data/ilenia/ilenia_reference.tsv $FLAGS --output-file results/ilenia/evaluation.tsv
python3 evaluate_iago.py $FLAGS --output-file results/iago/evaluation.tsv

# Inter-annotator agreement on Ilenia
A=data/ilenia/annotators
for pair in "$A/ilenia_annotator_1.tsv $A/ilenia_annotator_2.tsv annotator_1-vs-annotator_2" \
            "data/ilenia/ilenia_reference.tsv $A/ilenia_annotator_1.tsv reference-vs-annotator_1" \
            "data/ilenia/ilenia_reference.tsv $A/ilenia_annotator_2.tsv reference-vs-annotator_2"; do
    set -- $pair
    mkdir -p "results/iaa/$3"
    python3 interannotator_agreement.py "$1" "$2" \
        --output-file "results/iaa/$3/agreement.tsv" \
        --summary-file "results/iaa/$3/summary.tsv" \
        --disagreements-file "results/iaa/$3/disagreements.tsv"
done
