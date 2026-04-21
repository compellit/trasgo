"""
Add syllable breaks from stressed/unstressed phonological words
"""

import pandas as pd
import re
import csv
df = pd.read_csv("/home/anxo/compellit/silaba_gl/results/001.tsv", sep="\t")
df = df[df.correct]

VOWELS = ["a", "e", "i", "o", "u", "O", "E"]
SEMIVOWELS = ["j", "w"]
VOWELS_SEMI = VOWELS + SEMIVOWELS
STOPS_F = ["G", "B", "D", "t", "p", "k", "f", "g"]

def check_semiconsonant(sylls, i):
    """Check if next syllable starts with semiconsonant and
    add it to current syll if it does
    
    Args:
        sylls (list): list of syllables
        i (int): current syllable index
    """
    if i + 1 < len(sylls):
        if sylls[i+1][0] in SEMIVOWELS:
            if not (len(sylls[i+1]) > 1 and
            sylls[i+1][1] in VOWELS):
                sylls[i] += sylls[i+1][0]
                sylls[i+1] = sylls[i+1][1:]
        elif sylls[i+1][0] == "N":
            sylls[i] += sylls[i+1][0]
            sylls[i+1] = sylls[i+1][1:]



def mark_stress(sylls, stress_idx, deleted_syllables):
    """Return stress from stress index
    
    Args:
        sylls (list): list of syllables
        stress_idx (int): original position of stress
        deleted_syllables (int): number of syllables deleted before stress_idx
    """
    if len(sylls) > 1:
        if stress_idx == 0:
            sylls[0] = f"\\\"{sylls[0]}"
        else:
            sylls[stress_idx-deleted_syllables-1] += "\\\""
    else:
        sylls[0] = f"\\\"{sylls[0]}"

total_words = 0
total_correct = 0
correct = 0
output_dict = {}


for ortho, pred, gold in df[["forma", "silaba_output_raw","gold_sampa_preproc"]].itertuples(index=False):
    total_words += 1
    gold_s = gold
    dots = 0

    #add sylable break after each vowel
    for i, c in enumerate(gold_s):
        if c in VOWELS:
            dots += 1
            gold_s = gold_s[:i+dots] + "." + gold_s[i+dots:]

    sylls = re.split(r"\.|\\(\")", gold_s)
    sylls = [s for s in sylls if s]

    #eliminate accent but keep accent index
    if "\"" not in sylls:
        stress = True
        print(f"No accent for word {gold}")
        stress = False
    else:
        stress = True
        stress_idx = sylls.index("\"")
        sylls = sylls[:stress_idx] + sylls[stress_idx+1:]

    deleted_syllables = 0
    #the loop takes the codas from the next syllable to the correct one
    for i, syll in enumerate(sylls):

        #treat tS as one single sound
        syll = re.sub(r"tS", "4", syll)

        #for the first syllable only check if there's a semiconsonant in the next syllable
        if i == 0:
            check_semiconsonant(sylls, i)
            continue 

        #if there is no vowel in the syllable it's always the coda from the previous one
        if all(c not in VOWELS for c in syll):
            sylls[i-1] += syll
            #keep track of the deleted syllables for accent handling later
            if i < stress_idx:
                deleted_syllables += 1
            del(sylls[i])
            check_semiconsonant(sylls, i)
            continue 

        #check length until the nucleus
        len_cons = next((x for x, c in enumerate(syll) if c in VOWELS_SEMI), len(syll))

        #4 consonants can only happen when cluster coda and cluster onset meet
        if len_cons > 3:
            sylls[i-1] += syll[:2]
            sylls[i] = syll[2:]

        elif len_cons > 2:

            if (syll[0] not in VOWELS and
                    syll[1] not in VOWELS_SEMI
                    and syll[2] not in VOWELS_SEMI):
                
                #cluster coda always involves s
                if (syll[1] == "s"
                    or not
                    #any other set of consonants where the last two words cannot form
                    #an onset cluster (handle foreign word/cultism exceptions)
                    (syll[1] in STOPS_F + ["b", "d", "g"] and
                     syll[2] in ["l", "r"]) and not
                     syll[1:2] in ["dl", "tl"]):
                    sylls[i-1] += syll[:2]
                    sylls[i] = syll[2:]
                else:
                    sylls[i-1] += syll[:1]
                    sylls[i] = syll[1:]

        elif len_cons > 1:

            #check onset cluster
            if syll[0] not in VOWELS and syll[1] not in VOWELS_SEMI:
                if not(syll[0] in STOPS_F and
                     syll[1] in ["l", "r"] and not
                     syll[:1] in ["dl", "tl"]):
                    sylls[i-1] += syll[0]
                    sylls[i] = syll[1:]

        check_semiconsonant(sylls, i)

    if stress:
        mark_stress(sylls, stress_idx, deleted_syllables)

    syllabified_gold = ".".join(sylls).replace("4","tS")
    pred = pred.replace(".\\\"", "\\\".")
    correct = syllabified_gold == pred
    total_correct = total_correct + 1 if correct else total_correct
    if re.search(r"j\.[aeouOE]|[OEaeou]i|tl", pred):
        wrong_pred = True
    else:
        wrong_pred = False

    output_dict[ortho] = {
        "syllabified_gold": syllabified_gold.replace("\\\"", "\""),
        "pred": pred.replace("\\\"", "\""),
        "correct": correct,
        "wrong_pred": wrong_pred
    }

output_df = pd.DataFrame(output_dict)
output_df.T.to_csv("syllabification.tsv", sep="\t", quoting=csv.QUOTE_NONE, escapechar="\\")
print(total_correct/total_words)