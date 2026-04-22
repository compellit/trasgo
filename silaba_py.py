#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
LISTS_DIR = HERE / "listas"
LEMMA_DIR = LISTS_DIR / "lemma"


def load_list(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def search(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None


def sub(pattern: str, repl: str, text: str, count: int = 0) -> str:
    return re.sub(pattern, repl, text, count=count)


@dataclass
class SharedLists:
    lista_x: list[str]
    lista_2x: list[str]
    e_ton: list[str]
    e_pre: list[str]
    ee_pre: list[str]
    ee_caps_pre: list[str]
    o_ton: list[str]
    o_pre: list[str]
    oo_pre: list[str]
    oo_caps_pre: list[str]
    vbos_alt: list[str]
    nps_eo: list[str]
    suf: list[str]


@dataclass
class PortugueseLists(SharedLists):
    u_trema: list[str]
    lista_an: list[str]
    lista_ans: list[str]


@dataclass
class LemmaLists:
    inv: list[str]
    dup: list[str]
    lemma1: list[str]
    lemma2: list[str]
    i_ton: list[str]
    es_e: list[str]
    eses: list[str]
    vg: list[str]
    ie: list[str]
    res: list[str]


def load_shared_lists() -> SharedLists:
    return SharedLists(
        lista_x=load_list(LISTS_DIR / "lista-x.txt"),
        lista_2x=load_list(LISTS_DIR / "lista-duplo-x.txt"),
        e_ton=load_list(LISTS_DIR / "E-tonico.txt"),
        e_pre=load_list(LISTS_DIR / "E-pretonico.txt"),
        ee_pre=load_list(LISTS_DIR / "Ee-pretonico.txt"),
        ee_caps_pre=load_list(LISTS_DIR / "EE-pretonico.txt"),
        o_ton=load_list(LISTS_DIR / "O-tonico.txt"),
        o_pre=load_list(LISTS_DIR / "O-pretonico.txt"),
        oo_pre=load_list(LISTS_DIR / "Oo-pretonico.txt"),
        oo_caps_pre=load_list(LISTS_DIR / "OO-pretonico.txt"),
        vbos_alt=load_list(LISTS_DIR / "lista-vbo-EO-ton.txt"),
        nps_eo=load_list(LISTS_DIR / "lista-np-EO.txt"),
        suf=load_list(LISTS_DIR / "sufixos.txt"),
    )


def load_portuguese_lists() -> PortugueseLists:
    shared = load_shared_lists()
    return PortugueseLists(
        **shared.__dict__,
        u_trema=load_list(LISTS_DIR / "lista-u-trema.txt"),
        lista_an=load_list(LISTS_DIR / "lista-an.txt"),
        lista_ans=load_list(LISTS_DIR / "lista-ans.txt"),
    )


def load_lemma_lists() -> LemmaLists:
    dup_rows = [line.split() for line in load_list(LEMMA_DIR / "lista-duplas.txt")]
    return LemmaLists(
        inv=load_list(LEMMA_DIR / "lista-inv.txt"),
        dup=[row[0] for row in dup_rows],
        lemma1=[row[1] for row in dup_rows],
        lemma2=[row[2] for row in dup_rows],
        i_ton=load_list(LEMMA_DIR / "lista-is-i-ton.txt"),
        es_e=load_list(LEMMA_DIR / "lista-es-e.txt"),
        eses=load_list(LEMMA_DIR / "lista-eses-ese.txt"),
        vg=load_list(LEMMA_DIR / "lista-VG.txt"),
        ie=load_list(LEMMA_DIR / "lista-ie.txt"),
        res=load_list(LEMMA_DIR / "lista-res.txt"),
    )


def lemmatize(word: str, lemma_lists: LemmaLists) -> tuple[str | None, str | None]:
    if not word:
        return None, None

    token = word.lower()

    if token in lemma_lists.inv:
        return token, None

    for idx, dup in enumerate(lemma_lists.dup):
        if token == dup:
            return lemma_lists.lemma1[idx], lemma_lists.lemma2[idx]

    if token in lemma_lists.i_ton:
        return sub(r"ís$", "í", token), None

    if token in lemma_lists.es_e:
        return sub(r"es$", "e", token), None

    if token in lemma_lists.eses:
        return sub(r"eses$", "ese", token), None

    if token in lemma_lists.vg:
        return sub(r"is$", "i", token), None

    if token in lemma_lists.res:
        return sub(r"es$", "e", token), None

    if token in lemma_lists.ie:
        return sub(r"ies$", "ie", token), None

    if token == "abertzais":
        return "abertzale", None
    if search(r"ies$", token):
        return sub(r"ies$", "y", token), None
    if search(r"^.?[aeiou]les", token) or token == "aqueles":
        return sub(r"les$", "l", token), None
    if search(r"ís$", token):
        return sub(r"ís$", "il", token), None
    if search(r"[aeiouáéíóú]is$", token):
        return sub(r"([áéíóúaeiou])is$", r"\1l", token), None
    if search(r"(cal|fel|fol|gol|mal|mel|mil|mol|pel|ril|rol|sal|sol|tal|til|val|vil|xel)es$", token):
        return sub(r"les$", "l", token), None
    if search(r"[aeiouáéíóú]les$", token) and search(r"[áéíóú]", token):
        return sub(r"les$", "l", token), None
    if search(r"re?s$", token) or search(r"ces$", token):
        token = sub(r"rs$", "r", token)
        token = sub(r"res$", "r", token)
        token = sub(r"ces$", "z", token)
        return token, None
    if search(r"ns$", token):
        return sub(r"ns$", "n", token), None
    if search(r"ses$", token):
        token = sub(r"ses$", "s", token)
        if search(r"[aeiou]s$", token) and len(token) > 4 and not search(r"[áéíóú]", token):
            token = sub(r"as$", "ás", token)
            token = sub(r"es$", "és", token)
            token = sub(r"is$", "ís", token)
            token = sub(r"os$", "ós", token)
            token = sub(r"us$", "ús", token)
        elif search(r"[aeiou]s$", token):
            token = sub(r"as$", "as", token)
            token = sub(r"es$", "es", token)
            token = sub(r"is$", "is", token)
            token = sub(r"os$", "os", token)
            token = sub(r"us$", "us", token)
        else:
            token = sub(r"s$", "se", token)
        return token, None
    if search(r"[aeiouáéíóúy]s$", token):
        return sub(r"s$", "", token), None
    return sub(r"s$", "", token), None


class SilabaError(Exception):
    pass


class Silaba:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.lemma_lists = load_lemma_lists()
        self.shared = load_shared_lists()
        self.portuguese = load_portuguese_lists()

        self.entrada = ""
        self.entrada2: str | None = None
        self.entrada_lem: str | None = None
        self.entrada_lem2: str | None = None
        self.entrada_vbex: str | None = None
        self.input_word = ""
        self.palavra = ""
        self.deep = ""

    def run(self, word: str) -> str:
        if self.args.l:
            return self.run_portuguese(word)
        return self.run_ilg(word)

    def _load_lemma_if_plural(self) -> None:
        if search(r"s$", self.entrada):
            self.entrada_lem, self.entrada_lem2 = lemmatize(self.entrada, self.lemma_lists)

    def _finalize_output(self) -> str:
        self.apply_shared_postlexical_rules()
        if self.args.s:
            return sub(r'(")?\.', r"\1", self.palavra, count=1)
        return sub(r'(")?\.', r"\1", sub(r"\[[\w]*\]", "", self.palavra), count=1)

    def _set_deep(self) -> None:
        self.deep = sub(r"\[[^\]\[]+\]", "", self.palavra)
        self.deep = sub(r"\{|\}", "", self.deep)
        self.deep = sub(r'[\.\"]+', "", self.deep)

    def _maybe_return_deep(self) -> str | None:
        self._set_deep()
        if self.args.d:
            deep = self.deep
            if not self.args.t:
                deep = deep.replace("T", "s")
            return deep
        return None

    def _check_digits(self) -> None:
        if not search(r"\D", self.palavra):
            raise SilabaError("erro")

    def _common_syllable_markup(
        self,
        dip: list[str],
        nc: list[str],
        dig: list[str],
        atc: list[str],
        ats: list[str],
        cd: list[str],
        cdc: list[str],
        br_words: list[str],
        bl_words: list[str],
    ) -> None:
        # Diphthongs are marked as nucleus.
        for d in dip:
            if search(r"gi", self.palavra):
                self.palavra = sub(rf"(^|[^\]\{{gk])({re.escape(d)})", rf"\1{{\2}}[Nc]", self.palavra)
            else:
                self.palavra = sub(rf"(^|[^\]\{{])({re.escape(d)})", rf"\1{{\2}}[Nc]", self.palavra)

        # Vowels are marked as nucleus.
        for v in nc:
            pat = rf"([^\{{]|^)({re.escape(v)})([^\}}]|$)"
            self.palavra = sub(pat, r"\1{\2}[Nc]\3", self.palavra)
            self.palavra = sub(pat, r"\1{\2}[Nc]\3", self.palavra)

        # If word is BR/BL, split into coda/onset (no complex onset).
        for br in br_words:
            if search(br, self.entrada):
                self.palavra = sub(r"br", r"{b}[Cd]{R}[At]", self.palavra, count=1)
        for bl in bl_words:
            if search(bl, self.entrada):
                self.palavra = sub(r"bl", r"{b}[Cd]{l}[At]", self.palavra, count=1)

        # Digraphs are marked as onsets.
        for d in dig:
            pat = rf"([^\{{]|^)({re.escape(d)})([^\}}]|$)"
            self.palavra = sub(pat, r"\1{\2}[At]\3", self.palavra)
            self.palavra = sub(pat, r"\1{\2}[At]\3", self.palavra)

        # Complex onsets are marked.
        for onset in atc:
            self.palavra = sub(rf"({onset})", r"{\1}[At]", self.palavra)

        # Simple onsets are marked.
        for onset in ats:
            self.palavra = sub(
                rf"({re.escape(onset)})([aeiouáéíóúãõâêôwj\{{\}}]+)\[Nc\]",
                r"{\1}[At]\2[Nc]",
                self.palavra,
            )

        # Vocalized "k/g" have the "vowel" in the onset.
        if search(r"\{[gk]\}\[At\]\{w", self.palavra):
            self.palavra = sub(r"\{(g|k)\}\[At\]\{w\}\[Nc\]", r"{\1w}[At]", self.palavra)

        # Complex (and "strange") codas are marked.
        for c in cdc:
            self.palavra = sub(
                rf"([^\{{\[])(?:{re.escape(c)})([^\}}\]]|$)",
                lambda m, c=c: f"{m.group(1)}{{{c}}}[Cd]{m.group(2)}",
                self.palavra,
            )

        # Simple codas are marked.
        for c in cd:
            self.palavra = sub(
                rf"([^\{{\[])(?:{re.escape(c)})([^\}}\]]|$)",
                lambda m, c=c: f"{m.group(1)}{{{c}}}[Cd]{m.group(2)}",
                self.palavra,
            )

        if search(r"\{ng\}\[Cd\]\{s\}\[Cd\]", self.palavra):
            self.palavra = self.palavra.replace("{ng}[Cd]{s}[Cd]", "{ns}[Cd]")
        if search(r"\{r\}\[Cd\]\{s\}\[Cd\]", self.palavra) and (
            search(r"^persp|^perscr|^interst|^superst", self.entrada) or search(r"rs$", self.entrada)
        ):
            self.palavra = self.palavra.replace("{r}[Cd]{s}[Cd]", "{rs}[Cd]")

    def _split_syllables_and_stress_pt(self, aton: list[str]) -> None:

        if search(r"[kg]\}\[At\]\{u\}\[Nc\]\{(e|i|é|ê|í)", self.palavra):
            self.palavra = sub(r"(k|g)\}\[At\]\{u\}\[Nc\]\{(e|é|ê|i|í)", r"\1w}[At]{\2", self.palavra)

        # Special rule to parse "w/y(j)" as a glide.
        if search(r"{wi}", self.palavra):
            self.palavra = self.palavra.replace("{wi}", "{uj}")
        if search(r"\{[wj]\}\[Nc\]", self.palavra):
            self.palavra = sub(r"\{(w|j)\}\[Nc\]\{(a|e|i|o|u|á|é|í|ó|ú|â|ê|ô)\}", r"{\1\2}", self.palavra)
            self.palavra = sub(r"\{(a|e|i|o|u|á|é|í|ó|ú|â|ê|ô)\}\[Nc\]\{(w|j)\}\[Nc\]", r"{\1\2}[Nc]", self.palavra)

        # Special rule: diphthong before a coda different from "s" is hiatus.
        if search(r"\{[aeo][iu]\}\[Nc\]\{[^s]\}\[Cd\]", self.palavra):
            self.palavra = sub(r"\{([aeo])([iu])\}\[Nc\]\{([^s])\}\[Cd\]", r"{\1}[Nc]{\2}[Nc]{\3}[Cd]", self.palavra)

        self._finish_syllable_split()

        # Stress assignment.
        if search(r"(á|é|í|ó|ú|ã|õ|â|ê|ô)", self.palavra):
            self.palavra = sub(r"\.([^\.]+)?([áéíóúãõâêô])", r'".\1\2', self.palavra, count=1)
        elif search(r"([^slrmnaeioujw2])$", self.input_word):
            self.palavra = sub(r"\.([^\.]+)$", r'".\1', self.palavra, count=1)
        elif search(r"[^iujw][sm]$", self.input_word) or search(r"[aeo]\[Nc\]$", self.palavra):
            self.palavra = sub(r'^\.(..?)?(\[At\])?(a|e|o)\[Nc\](s|m)?(\[Cd\])?$', r'".\1\2\3[Nc]\4\5', self.palavra)
            self.palavra = sub(r"\.([^\.]+)\.([^\.]+)$", r'".\1.\2', self.palavra, count=1)
        else:
            self.palavra = sub(r"\.([^\.]+)$", r'".\1', self.palavra, count=1)

        # Unstressed words: remove the accent.
        if self.entrada in aton:
            self.palavra = self.palavra.replace('"', "")

        self.palavra = self.palavra.replace("á", "a").replace("â", "6").replace("é", "E")
        self.palavra = self.palavra.replace("ê", "e").replace("í", "i").replace("ó", "O")
        self.palavra = self.palavra.replace("ô", "o").replace("ú", "u")

        # Pre-stressed "i.o" to "io" (confesional).
        if search(r"[sxc]io", self.entrada):
            self.palavra = self.palavra.replace("]i[Nc].o[Nc]\"", "]io[Nc]\"")

    def _split_syllables_and_stress_ilg(self, aton: list[str]) -> None:
        # Special rule to diphthongize words with "ial".
        if search(r"ial", self.entrada) and not search(r"^sial$|^dial|^trial$|^marial$|^antial|^afial|ialdade|^mial", self.entrada):
            self.palavra = self.palavra.replace("{i}[Nc]{a}[Nc]{l}", "{ia}[Nc]{l}")

        if search(r"[kg]\}\[At\]\{u\}\[Nc\]\{(e|i|é|í)", self.palavra):
            self.palavra = sub(r"(k|g)\}\[At\]\{u\}\[Nc\]\{(e|é|i|í)", r"\1w}[At]{\2", self.palavra)

        # Special rules to parse words with "w/y(j)" as a glide.
        if search(r"{wi}", self.palavra):
            self.palavra = self.palavra.replace("{wi}", "{uj}")
        if search(r"\{[wj]\}\[Nc\]", self.palavra):
            self.palavra = sub(r"\{(j|w)\}\[Nc\]\{(a|e|i|o|u|á|é|í|ó|ú|â|ê|ô)\}", r"{\1\2}", self.palavra)
            self.palavra = sub(r"\{(a|e|i|o|u|á|é|í|ó|ú|â|ê|ô)\}\[Nc\]\{(w|j)\}\[Nc\]", r"{\1\2}[Nc]", self.palavra)

        self._finish_syllable_split()

        # Stress assignment.
        if search(r"á|é|í|ó|ú", self.palavra):
            self.palavra = sub(r"\.([^\.]+)?([áéíóú])", r'".\1\2', self.palavra, count=1)
        elif not search(r"(n|s)\[Cd\]$", self.palavra) and search(r"\[Cd\]$", self.palavra):
            self.palavra = sub(r"\.([^\.]+)$", r'".\1', self.palavra, count=1)
        elif search(r"[^aeo][iu]\[Nc\]\.[aeo]\[Nc\]([ns]+\[Cd])?$", self.palavra):
            self.palavra = sub(r"\.([^\.]+)\.([^\.]+)(i|u)\[Nc\]\.(a|e|o)\[Nc\]([ns]+\[Cd])?$", r'".\1.\2\3[Nc].\4[Nc]\5', self.palavra)
        elif search(r"[iu]?[aeoiu]\[Nc\]([ns]+\[Cd\])?$", self.palavra):
            self.palavra = sub(r"\.([^\.]+)\.([^\.]+)$", r'".\1.\2', self.palavra)
            self.palavra = sub(r"^\.([^\.]+)$", r'".\1', self.palavra)
        else:
            self.palavra = sub(r"\.([^\.]+)$", r'".\1', self.palavra)

        # Unstressed words: remove the accent.
        if self.entrada in aton:
            self.palavra = self.palavra.replace('"', "")

        self.palavra = self.palavra.replace("á", "a").replace("é", "e").replace("í", "i")
        self.palavra = self.palavra.replace("ï", "i").replace("ó", "o").replace("ú", "u")


        # High vowel + stressed vowel
        if search(r"\"(\.)?([^\[]{,2}\[At\])?[iu]([aeoEO])", self.palavra):
            if not (search(r"ial", self.entrada) and not search(r"^sial$|^dial|^trial$|^marial$|^antial|^afial|ialdade|^mial", self.entrada) or
                    search(r"ións?$", self.entrada) or search(r"[scx]ion", self.entrada) or
                    search(r"[xcs]io", self.entrada) or search(r"iar$", self.entrada)):
                self.palavra = sub(r"(\")(\.)?([^\[]{,2}\[At\])?([iu])([aeoEO])",r"\2\3\4[Nc]\1.\5", self.palavra)

        # u.al (+suffix)
        no_suf = self.entrada
        for suf in sorted(self.shared.suf, key=len, reverse=True):
            if self.entrada.endswith(suf):
                no_suf = self.entrada[:-len(suf)]
                break
        if no_suf.endswith("ual"):
             self.palavra = sub(r"ua\[Nc\](l|\.l)",r"u[Nc].a[Nc]\1", self.palavra)
        # # Special rule to diphthongize words with "ial".
        # if search(r"ial", self.entrada) and not search(r"^sial$|^dial|^trial$|^marial$|^antial|^afial|ialdade|^mial", self.entrada):
        #     self.palavra = self.palavra.replace("{i}[Nc]{a}[Nc]{l}", "{ia}[Nc]{l}")

        # # Words ending in -ción/xión/sión (and with internal "cion"): diphthong.
        # if search(r"[cxs]ións?$", self.entrada) or search(r"[scx]ion", self.entrada):
        #     self.palavra = sub(r"\.(s|T)\[At\]i\[Nc\]\"\.o\[Nc\]", r'".\1[At]jo[Nc]', self.palavra)
        #     self.palavra = sub(r"\.(s|T)\[At\]i\[Nc\]\.o\[Nc\]\.n\[At\]", r".\1[At]jo[Nc].n[At]", self.palavra)
        # # Pre-stressed "i.o" to "io" (confesional).
        # if search(r"[xcs]io", self.entrada):
        #     self.palavra = self.palavra.replace("]i[Nc].o[Nc]\"", "]jo[Nc]\"")

    def _finish_syllable_split(self) -> None:
        # Inserts a vowel or deletes the first onset (psicólogo).
        if search(r"^([^\{])\{([^\}]*)\}\[At\]", self.palavra):
            self.palavra = sub(r"^([^\{])\{([^\}]*)\}\[At\]", r"{\2}[At]", self.palavra)
        # "Strange codas": foreign words ending in onsets: onset > coda.
        if search(r"\{tS\}\[At\]$", self.palavra):
            self.palavra = self.palavra.replace("{tS}[At]", "{tS}[Cd]")

        # If there are any elements outside the constituents, the word was not well parsed.
        if (
            search(r"\]([^\{\ \.]+)(\{|$)", self.palavra)
            or search(r"At\]\{..?\}\[At\]", self.palavra)
            or search(r"Cd\]\{..?\}\[Cd\]", self.palavra)
            or search(r"\[At\]$", self.palavra)
            or search(r"^[^\{]", self.palavra)
        ):
            raise SilabaError("erro")

        # Constituent marks are removed.
        self.palavra = self.palavra.replace("{", "").replace("}", "")

        # Syllable splitter.
        self.palavra = sub(r"([^\]]+)\[At\]", r".\1[At]", self.palavra)
        self.palavra = sub(r"^([^\]]+)\[Nc\]", r".\1[Nc]", self.palavra)
        self.palavra = sub(r"([^\]]+)\[Nc\]([^\.\[]+)\[Nc\]", r"\1[Nc].\2[Nc]", self.palavra)
        self.palavra = sub(r"([^\]]+)\[Nc\]([^\.\[]+)\[Nc\]", r"\1[Nc].\2[Nc]", self.palavra)
        self.palavra = sub(r"Cd\]([^\.\[]+)\[Nc\]", r"Cd].\1[Nc]", self.palavra)

    def _apply_vowel_lookups(self, shared: SharedLists) -> None:
        if search(r"^quent", self.entrada):
            self.palavra = sub(r'^(")?\.k\[At\]e\[Nc\]', r"\1.k[At]E[Nc]", self.palavra)
        elif search(r"^vot", self.entrada):
            self.palavra = sub(r'^(")?\.b\[At\]o\[Nc\]', r"\1.b[At]O[Nc]", self.palavra)
        elif search(r"equilib", self.entrada):
            self.palavra = self.palavra.replace("e[Nc].k[At]", "E[Nc].k[At]")
        elif search(r"electr", self.entrada):
            self.palavra = sub(r'e\[Nc\](")?\.l\[At\]e\[Nc\]', r'E[Nc]\1.l[At]E[Nc]', self.palavra)

        self._apply_lookup_list(shared.e_ton, r'"\.([^\.]+)?e', r'".\1E', stressed=True)
        self._apply_lookup_list(shared.e_pre, r'e([^\"e]*)\"', r'E\1"', prestressed=True)
        self._apply_lookup_list(shared.ee_pre, r'e([^\"e]*)e([^\"e]*)\"', r'E\1e\2"', prestressed=True)
        self._apply_lookup_list(shared.ee_caps_pre, r'e([^\"e]*)e([^\"e]*)\"', r'E\1E\2"', prestressed=True)
        self._apply_lookup_list(shared.o_ton, r'"\.([^\.]+)?o', r'".\1O', stressed=True, support_entrada2=True)
        self._apply_lookup_list(shared.o_pre, r'o([^\"o]*)\"', r'O\1"', prestressed=True)
        self._apply_lookup_list(shared.oo_pre, r'o([^\"o]*)o([^\"o]*)\"', r'O\1o\2"', prestressed=True)
        self._apply_lookup_list(shared.oo_caps_pre, r'o([^\"o]*)o([^\"o]*)\"', r'O\1O\2"', prestressed=True)

        for token in shared.vbos_alt:
            if self.entrada == token:
                self.palavra = sub(r'"\.([^\.]+)?o', r'".\1O', self.palavra)
                self.palavra = sub(r'"\.([^\.]+)?e', r'".\1E', self.palavra)
            elif self.entrada_vbex and re.fullmatch(token, self.entrada_vbex):
                self.palavra = sub(r'"\.([^\.]+)?o', r'".\1O', self.palavra)
                self.palavra = sub(r'"\.([^\.]+)?e', r'".\1E', self.palavra)
                self.palavra = sub(r"([^-])$", r"\1-", self.palavra)

        for token in shared.nps_eo:
            if self.entrada == token:
                self.palavra = sub(r'"\.([^\.]+)?o', r'".\1O', self.palavra)
                self.palavra = sub(r'"\.([^\.]+)?e', r'".\1E', self.palavra)

    def _apply_lookup_list(
        self,
        values: list[str],
        pattern: str,
        replacement: str,
        *,
        stressed: bool = False,
        prestressed: bool = False,
        support_entrada2: bool = False,
    ) -> None:
        for token in values:
            if self.entrada == token:
                self.palavra = sub(pattern, replacement, self.palavra)
            elif self.entrada_lem or self.entrada_lem2:
                if self.entrada_lem == token or self.entrada_lem2 == token:
                    self.palavra = sub(pattern, replacement, self.palavra)
            if support_entrada2 and self.entrada2 and self.entrada2 == token:
                if stressed:
                    self.palavra = sub(r"o([^o]*)\"", r'O\1"', self.palavra)
                else:
                    self.palavra = sub(r"e([^e]*)\"", r'E\1"', self.palavra)
            elif stressed and self.entrada2 and self.entrada2 == token and "e" in pattern:
                self.palavra = sub(r"e([^e]*)\"", r'E\1"', self.palavra)

    def apply_shared_postlexical_rules(self) -> None:
        # Oral diphthongs.
        self.palavra = sub(r"([aeouEO])[ij]|[ij]([aeouE])", r"\1j\2", self.palavra)
        self.palavra = sub(r"([aeoE])u|u([aeouEO])", r"\1w\2", self.palavra)
        self.palavra = self.palavra.replace("]ia[", "]ja[")
        self.palavra = sub(r"\]a\[Nc\]\.o\[Nc\](s\[Cd\])?", r"]aw[Nc]\1", self.palavra)

        # Complex codas.
        if not self.args.c:
            self.palavra = sub(r'n\[Cd\](")?\.n\[At\]', r"\1.n[At]", self.palavra)
            self.palavra = sub(r'g\[Cd\](")?\.n\[At\]', r'n[Cd]\1.n[At]', self.palavra)
            self.palavra = sub(r"\](p|k|t|b|d|g|f)\[Cd\]", r"]", self.palavra)
            self.palavra = sub(r"(gs|bs|ds|ks|st)\[Cd\]", r"s[Cd]", self.palavra)
            self.palavra = sub(r"([rn])[gk]\[Cd\]", r"\1[Cd]", self.palavra)
            self.palavra = sub(r"rs\[Cd\]$", r"r[Cd]", self.palavra)
            self.palavra = sub(r"r[kd]\[Cd\]", r"r[Cd]", self.palavra)
            self.palavra = sub(r"[rtlpk]s\[Cd\]", r"s[Cd]", self.palavra)
            self.palavra = sub(r"(r|n)t\[Cd\]", r"\1[Cd]", self.palavra)
            self.palavra = sub(r"[nN]\[Nc\]s\[Cd\](.)", r"[Nc]s[Cd]\1", self.palavra)
            self.palavra = sub(r"[nN]s\[Cd\](.)", r"s[Cd]\1", self.palavra)
            self.palavra = sub(r"l[fk]\[Cd\]", r"l[Cd]", self.palavra)
            self.palavra = sub(r"n[pb]\[Cd\]", r"n[Cd]", self.palavra)
            self.palavra = sub(r"tS\[Cd\]$", r"s[Cd]", self.palavra)
            if search(r"(á|é|í|ó|ú)", self.palavra) and not search(r"(á|é|í|ó|ú)\[Nc\][nN]s\[Cd\]$", self.palavra):
                self.palavra = sub(r"[nN]s\[Cd\]$", r"s[Cd]", self.palavra)

        # Flag -t: thetacism.
        if not self.args.t:
            self.palavra = self.palavra.replace("T", "s")

        # Flag -h: gheada.
        if self.args.h:
            self.palavra = sub(r'n\[Cd\](")?\.\g', "", self.palavra) if False else self.palavra
            self.palavra = sub(r'n\[Cd\](")?\.g', r'n[Cd]\1.k', self.palavra)
            self.palavra = self.palavra.replace("g", "H")

        # Post-lexical rules.
        if self.args.r:
            self.palavra = sub(r's\[Cd\](")?\.([bdgfjmnSsJlLT])', r'r[Cd]\1.\2', self.palavra)
            self.palavra = sub(r's\[Cd\](")?\.R', r"\1.R", self.palavra)
        else:
            self.palavra = sub(r's\[Cd\](")?\.([bdg])', r'z[Cd]\1.\2', self.palavra)
            if not self.args.t:
                self.palavra = sub(r'\]s\[Cd\](")?\.s\[At\]', r"]\1.s[At]", self.palavra)

        self.palavra = self.palavra.replace("bs[Cd]", "Bs[Cd]").replace("ds[Cd]", "Ds[Cd]")
        self.palavra = sub(r'(Nc\]|[srl]\[Cd\])(")?\.g', r"\1\2.G", self.palavra)
        self.palavra = sub(r'(Nc\]|[sr]\[Cd\])(")?\.d', r"\1\2.D", self.palavra)
        self.palavra = sub(r'(Nc\]|[srl]\[Cd\])(")?\.b', r"\1\2.B", self.palavra)
        self.palavra = sub(r"\[Nc\]ns\[Cd\]$", r"N\[Nc]s[Cd]", self.palavra)

        # Broad representation.
        if not self.args.b:
            self.palavra = sub(r'l(\[Cd\])(")?(\.[gGk]|$)', r"5\1\2\3", self.palavra)
            # self.palavra = self.palavra.replace("l[Cd]", "5[Cd]")
            self.palavra = self.palavra.replace("s", "_s")

        # Vowels.
        for vowel in "aeiou":
            self._apply_vowel_surface_rules(vowel)

        # Implosive nasal: velar.
        # self.palavra = sub(r"n(.)?\[Cd\]", r"N\1[Cd]", self.palavra)
        self.palavra = sub(r"[nm](\[Cd\]$)", r"N\1", self.palavra)
        self.palavra = sub(r"[nm](\[Cd\]\"?\.[gknm])", r"N\1", self.palavra)
        self.palavra = sub(r"[nm](\[Cd\]\"?\.[pb])", r"m\1", self.palavra)
        self.palavra = sub(r"[nm](\[Cd\]\"?\.f)", r"F\1", self.palavra)
        # self.palavra = sub(r"[nm](\[Cd\]\"?\.t?S)", r"J\1", self.palavra)
        
        

        # Nasalized vowel:
        # (1) between two nasal segments
        # (2) beginning
        # (3) with a nasal segment into the nucleus
        # (4) in inho/a(s)
        self.palavra = sub(r"(J|m|n)\[At\](a|e|i|o|u|A|E|I|O|U)\[Nc\]N", r"\1[At]\2~[Nc]N", self.palavra)
        self.palavra = sub(r"(J|m|n)\[At\](a|e|i|o|u|A|E|I|O|U)N\[Nc\]", r"\1[At]\2~N[Nc]", self.palavra)
        self.palavra = sub(r"(a|e|i|o|u|A|E|I|O|U)N\\\[Nc\]", r"\1~N\[Nc]", self.palavra)
        self.palavra = sub(r'^(")?\.(a|e|i|o|u|A|E|I|O|U)\[Nc\]N', r"\1.\2~[Nc]N", self.palavra)

        if search(r"iñ[oa]s?$", self.entrada):
            self.palavra = self.palavra.replace("]i[Nc].J[At]", "]i~[Nc].J[At]")

        if (self.entrada == "ó" or self.entrada == "ós") and self.args.i:
            self.palavra = self.palavra.replace('"', "")

    def _apply_vowel_surface_rules(self, vowel: str) -> None:
        accented = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}[vowel]
        if vowel not in self.palavra:
            return
        self.palavra = sub(rf'^(")?\.{vowel}', rf"\1.{accented}", self.palavra)
        self.palavra = sub(rf"{vowel}N\\\[Nc\]", f"{accented}N\\[Nc]", self.palavra)
        self.palavra = sub(rf"{vowel}\[Nc\]([5ln])", rf"{accented}[Nc]\1", self.palavra)
        if vowel in "aeo":
            self.palavra = sub(rf"{vowel}(j|w)", rf"{accented}\1", self.palavra)
            self.palavra = sub(rf"([jw]){vowel}", rf"\1{accented}", self.palavra)
        elif vowel == "u":
            self.palavra = self.palavra.replace("uj", "új")
        self.palavra = sub(rf'"(\.)?([^\.]+)?{vowel}\[Nc\]', rf'"\1\2{accented}[Nc]', self.palavra)
        self.palavra = self.palavra.replace(accented, vowel)

    def run_portuguese(self, word: str) -> str:
        dip = ["ai", "ái", "au", "áu", "ei", "éi", "eu", "éu", "ou", "óu", "oi", "ói", "ui"]
        nc = ["a", "e", "i", "o", "u", "á", "é", "í", "ó", "ú", "â", "ê", "ô", "w", "j"]
        dig = ["tS"]
        atc = [r"[kpbvfgtd](r|l)"]
        ats = ["b", "d", "g", "p", "t", "k", "s", "T", "f", "l", "L", "m", "n", "J", "r", "R", "S"]
        cd = ["s", "l", "m", "r", "n", "N", "b", "d", "g", "T"]
        cdc = ["gs", "ks", "bs", "ds", "ns", "ng", "nk", "np", "nt", "nb", "rg", "rk", "rs", "rt", "rd", "st", "ts", "lf", "ls", "lk", "ps", "ks", "k", "p", "f", "t"]
        br_words = ["abrog", "subrep", "subrog", "subruti", "subroti"]
        bl_words = ["oblong", "ablegad", "sublimin", "subling", "subluna", "subliñ"]
        aton = ["com", "que", "en", "me", "te", "lle", "se", "o", "a", "os", "as", "de", "sen", "che", "llo", "lla", "lles", "llos", "cho", "cha", "chos", "chas", "por", "e", "mas"]
        agem = ["aldragem", "apagem", "arragem", "atarragem", "avantagem", "degagem", "desencoragem", "desengragem", "desgagem", "deslagem", "encoragem", "engraxem", "malagem", "relaxem", "tarragem", "tagem", "tragem"]
        vbex = ["dispõe", "expõe", "impõe", "interpõe", "opõe", "pospõe", "pressupõe", "propõe", "repõe", "supõe", "põe", "predispõe"]
        vbex2 = ["dispões", "expões", "impões", "interpões", "opões", "pospões", "pressupões", "propões", "repões", "supões", "pões", "predispões"]

        self.entrada = word.lower()
        self.input_word = self.entrada
        self.palavra = self.entrada

        for token in vbex:
            if search(token, self.entrada):
                self.entrada_vbex = self.entrada

        self.entrada = sub(r"^novelo(s)?$", r"nobelo\1", self.entrada)
        for token in vbex2:
            if search(token, self.entrada):
                self.entrada = sub(r"pões", "pós", self.entrada)
                self.palavra = sub(r"pões", "pós", self.palavra)
        if search(r"disse(r)?|disser[ao](m|s)?|disser(des|mos)|dissere(m|s)|dissesse(m|s)?|disseste(s)?", self.entrada):
            if search(r"^disse|^contrad|^anted|^bend|^cond|^desd|^entred|^mald|^pred|^red", self.entrada):
                self.entrada = sub(r"diss", "dix", self.entrada)
                self.palavra = sub(r"diss", "dix", self.palavra)
        if search(r"^possa(m|s)?$|^possais$|^possamos$", self.entrada):
            self.entrada = sub(r"poss", "pod", self.entrada)
            self.palavra = sub(r"poss", "pod", self.palavra)
        self.palavra = sub(r"^posso$", "podo", self.palavra)
        self.entrada = sub(r"^posso$", "posso2", self.entrada)
        self.palavra = sub(r"põem$", "ponhem", self.palavra)
        self.entrada = sub(r"põem$", "poñen", self.entrada)
        self.entrada = sub(r"m2$", "n2", self.entrada)
        self.palavra = sub(r"^elixir$", "elixir2", self.palavra)
        self.entrada = sub(r"^elixir$", "elixir2", self.entrada)
        self.palavra = sub(r"^mãe(s)?$", r"mai\1", self.palavra)
        self.entrada = sub(r"^mãe(s)?$", r"mai\1", self.entrada)
        self.palavra = sub(r"erom$", "êron", self.palavra)
        self.entrada = sub(r"erom$", "eron", self.entrada)
        if not search(r"boom|zoom", self.palavra):
            self.palavra = sub(r"om$", "ón", self.palavra)
        if self.palavra in {"ontem", "ordem"}:
            self.palavra = sub(r"m$", "", self.palavra)
            self.entrada = sub(r"m$", "", self.entrada)
        self.palavra = sub(r"agem$", "age", self.palavra)
        if self.entrada in agem:
            self.palavra = sub(r"age$", "agem", self.palavra)
        if search(r"^vie[sr]", self.entrada):
            self.entrada = sub(r"^vie", "vinhe", self.entrada)
            self.palavra = sub(r"^vie", "vinhe", self.palavra)
        elif self.entrada == "veio":
            self.palavra = "veu"
        if self.palavra in {"à", "às"}:
            self.palavra = self.palavra.replace("à", "á")
        if not search(r"^pressas?$|^ossos?$", self.entrada):
            self.entrada = sub(r"ss", "s", self.entrada)
        self.palavra = sub(r"^sim$", "si", self.palavra)
        self.entrada = sub(r"^fiz([aeiouáéíê])", r"fix\1", self.entrada)
        self.palavra = sub(r"^fiz([aeiouáéíê])", r"fix\1", self.palavra)
        self.entrada = sub(r"^quis([aeiouê])", r"quix\1", self.entrada)
        self.palavra = sub(r"^quis([aeiouê])", r"quix\1", self.palavra)
        self.palavra = sub(r"^quis$", "quixem", self.palavra)
        self.palavra = sub(r"^quis2$", "quixo", self.palavra)
        self.palavra = sub(r"^fiz$", "fixem", self.palavra)
        self.palavra = sub(r"^fez$", "fixo", self.palavra)
        self.palavra = sub(r"^(v|t)êm$", r"\1énhem", self.palavra)
        self.palavra = sub(r"^(v|l)êem", r"\1êm", self.palavra)
        self.palavra = sub(r"ss", "s", self.palavra)
        self.entrada = sub(r"am$", "on", self.entrada)
        self.entrada = sub(r"ç", "z", self.entrada)
        self.entrada = sub(r"[çz]ão", "ción", self.entrada)
        self.entrada = sub(r"xão", "xión", self.entrada)
        self.entrada = sub(r"z(e|i|é|ê|í)", r"c\1", self.entrada)
        self.entrada = sub(r"nh", "ñ", self.entrada)
        self.entrada = sub(r"lh", "ll", self.entrada)
        self.entrada = sub(r"g([eiêéí])", r"x\1", self.entrada)
        self.entrada = sub(r"j", "x", self.entrada)
        self.entrada = sub(r"([^i])õe", r"\1ion", self.entrada)
        self.entrada = self.entrada.replace("â", "á").replace("ê", "é").replace("ô", "ó")

        if search(r"(â|ê|ô|á|é|í|ó|ú)(n|l|r|s)?ci(a|o)(s)?$", self.entrada):
            self.entrada = sub(r"(â|á)(n|l|r|s)?ci(a|o)(s)?$", r"a\2ci\3\4", self.entrada)
            self.entrada = sub(r"(ê|é)(n|l|r|s)?ci(a|o)(s)?$", r"e\2ci\3\4", self.entrada)
            self.entrada = sub(r"(ô|ó)(n|l|r|s)?ci(a|o)(s)?$", r"o\2ci\3\4", self.entrada)
            self.entrada = sub(r"í(n|l|r|s)?ci(a|o)(s)?$", r"i\1ci\2\3", self.entrada)
            self.entrada = sub(r"ú(n|l|r|s)?ci(a|o)(s)?$", r"u\1ci\2\3", self.entrada)

        if search(r"(â|ê|ô|á|é|í|ó|ú).i(a|o)(s)?$", self.entrada):
            self.entrada = sub(r"(â|á)(.)i(a|o)(s)?$", r"a\2i\3\4", self.entrada)
            self.entrada = sub(r"(ô|ó)(.)i(a|o)(s)?$", r"o\2i\3\4", self.entrada)
            self.entrada = sub(r"(ê|é)(.)i(a|o)(s)?$", r"e\2i\3\4", self.entrada)
            self.entrada = sub(r"í(.)i(a|o)(s)?$", r"i\1i\2\3", self.entrada)
            self.entrada = sub(r"ú(.)i(a|o)(s)?$", r"u\1i\2\3", self.entrada)

        if self.entrada != "vem":
            self.entrada = sub(r"([^o])m$", r"\1n", self.entrada)

        if search(r"[aei]rão$", self.entrada) and search(r"canelão|casarão|colherão|jantarão|jazerão|marrão|militarão|passarão|porão|são|travessão", self.input_word):
            self.entrada = sub(r"rão", "rán", self.entrada)
            self.palavra = sub(r"rão", "rán", self.palavra)
        else:
            self.entrada = sub(r"ão", "ón", self.entrada)
        self.entrada = sub(r"ã([^i]|$)", r"án\1", self.entrada)

        if search(r"(eiro|eira|iño|iña|ciño|ciña|mente|ito|ita)", self.entrada):
            self.entrada2 = self.entrada
            for pat, repl in [
                (r"eiros?$", "o"), (r"ciños?$", ""), (r"iños?$", "o"), (r"citos?$", ""),
                (r"itos?$", "o"), (r"eiras?$", "a"), (r"ciñas?$", ""), (r"iñas?$", "a"),
                (r"citas?$", ""), (r"itas?$", "a"), (r"mente$", "")
            ]:
                self.entrada2 = sub(pat, repl, self.entrada2)

        self._load_lemma_if_plural()

        if self.entrada in self.portuguese.lista_x:
            self.palavra = sub(r"x", "ks", self.palavra)
        if self.entrada in self.portuguese.lista_2x:
            self.palavra = sub(r"x([^x]+)(g|x)", r"ks\1S", self.palavra)
        if self.entrada in self.portuguese.u_trema:
            self.palavra = sub(r"gu([eéêií])", r"gw\1", self.palavra)
            self.palavra = sub(r"qu([eéêií])", r"kw\1", self.palavra)

        if search(r"á|é|í|ó|ú|â|ê|ô", self.palavra) and search(r"ã|õ", self.palavra):
            if self.palavra == "bênção" or self.palavra == "bênções":
                self.palavra = self.palavra.replace("bênção", "benção").replace("bênções", "benções")
            else:
                for pat, repl in [(r"ão$", "o"), (r"ãos$", "os"), (r"ões$", "os"), (r"ã$", "a"), (r"ãs$", "as")]:
                    self.palavra = sub(pat, repl, self.palavra)
        if search(r"ãi", self.palavra):
            self.palavra = sub(r"ãib", "anb", self.palavra)
        else:
            self.palavra = sub(r"ãi", "ai", self.palavra)
        self.palavra = sub(r"ães$", "áns", self.palavra)
        self.palavra = sub(r"ões$", "ôns", self.palavra)

        if search(r"ón$", self.entrada):
            entrada_tmp = sub(r"ón", "án", self.entrada)
            if entrada_tmp in self.portuguese.lista_an:
                self.palavra = sub(r"ão", "án", self.palavra)
        elif self.entrada2 and search(r"ón$", self.entrada2):
            entrada_tmp = sub(r"ón", "án", self.entrada2)
            if entrada_tmp in self.portuguese.lista_an:
                self.palavra = sub(r"ão", "an", self.palavra)

        if search(r"óns$", self.entrada):
            entrada_tmp = sub(r"óns", "áns", self.entrada)
            if entrada_tmp in self.portuguese.lista_ans:
                self.palavra = sub(r"ão", "an", self.palavra)

        if search(r"áns?$", self.entrada):
            self.palavra = sub(r"ão(s)?$", r"ôn\1", self.palavra)
        if search(r"2$", self.palavra):
            self.palavra = sub(r"ão2$", "án", self.palavra)
            self.palavra = sub(r"2$", "", self.palavra)

        self.palavra = sub(r"^cee$", "cé", self.palavra)
        self.palavra = sub(r"(^|[^cnlm])h", r"\1", self.palavra)
        self.palavra = sub(r"ck", "k", self.palavra)
        self.palavra = sub(r"ff", "f", self.palavra)
        self.palavra = sub(r"pp", "p", self.palavra)
        self.palavra = sub(r"ll", "l", self.palavra)

        if search(r"umh?a", self.palavra):
            self.palavra = sub(r"algumh?a", "alguNa", self.palavra)
            self.palavra = sub(r"nengumh?a", "nenguNa", self.palavra)
            self.palavra = sub(r"nenhumh?a", "nenhuNa", self.palavra)
            self.palavra = sub(r"^([dnc]?)umh?a(s)?$", r"\1uNa\2", self.palavra)
        elif search(r"mh", self.palavra):
            self.palavra = sub(r"mh", "m", self.palavra)

        self.palavra = self.palavra.replace("kiwi", "kivi").replace("kuwait", "kuvait")
        for pat, repl in [
            (r"ch", "tS"), (r"v", "b"), (r"(z|ç)", "T"), (r"c(e|é|ê|i|í)", r"T\1"),
            (r"c", "k"), (r"qu", "k"), (r"qú", "kú"), (r"g(e|é|ê|i|í)", r"S\1"),
            (r"gu(e|é|ê|i|í)", r"g\1"), (r"j", "S"), (r"nh", "J"), (r"lh", "L"),
            (r"^r", "R"), (r"rr", "R"), (r"(n|m|l|s)r", r"\1R"),
            (r"m([^aeiouáéíóúwjãõêâô])?$", r"n\1"), (r"m([^aeiouáéíóúwjãõêâô])", r"n\1"),
            (r"ãe(.)", r"an\1"), (r"ão(.)", r"on\1"), (r"ã", "án"), (r"õ", "ón"),
            (r"x$", "ks"), (r"x(p|t|k|b|d|g|T|f|s)", r"ks\1"), (r"x", "S"), (r"y", "j")
        ]:
            self.palavra = sub(pat, repl, self.palavra)

        if search(r"[kg]u[ao]", self.palavra):
            self.palavra = sub(r"([kg])u([ao])", r"\1w\2", self.palavra)
        if search(r"[kg]u(ou|ei|ai|au|oi)", self.palavra):
            self.palavra = sub(r"ku(ou|ei|ai|au|oi)", r"kw\1", self.palavra)
            self.palavra = sub(r"gu(ou|ei|ai|au|oi)", r"gw\1", self.palavra)

        self._check_digits()
        self._common_syllable_markup(dip, nc, dig, atc, ats, cd, cdc, br_words, bl_words)
        self._split_syllables_and_stress_pt(aton)
        self._apply_vowel_lookups(self.portuguese)
        deep = self._maybe_return_deep()
        if deep is not None:
            return deep
        return self._finalize_output()

    def run_ilg(self, word: str) -> str:
        dip = ["ai", "ái", "au", "áu", "ei", "éi", "eu", "éu", "ou", "óu", "oi", "ói", "ui",
               "ia", "iá", "ua", "uá", "ie", "ié", "ue", "ué", "uo", "uó", "io", "ió", "iu"]
        nc = ["a", "e", "i", "o", "u", "á", "é", "í", "ó", "ú", "w", "ï", "j"]
        dig = ["tS"]
        atc = [r"[kpbvfgtd](r|l)"]
        ats = ["b", "d", "g", "p", "t", "k", "s", "T", "f", "l", "L", "m", "n", "J", "r", "R", "S"]
        cd = ["s", "l", "r", "n", "m", "N", "b", "d", "g", "T"]
        cdc = ["gs", "ks", "bs", "ds", "ns", "ng", "nk", "np", "nt", "nb", "rg", "rk", "rt", "rs", "rd", "st", "ts", "lf", "ls", "lk", "ps", "ks", "k", "p", "f", "t"]
        br_words = ["abroga", "subrep", "subroga", "subruti", "subroti"]
        bl_words = ["oblong", "ablegad", "sublimin", "subling", "subluna", "subliñ"]
        aton = ["con", "que", "en", "me", "te", "lle", "se", "o", "a", "os", "as", "de", "sen", "che", "llo", "lla", "lles", "llos", "cho", "cha", "chos", "chas", "por", "e", "mais"]

        self.entrada = word.lower()
        self.input_word = self.entrada
        self.palavra = self.entrada

        if search(r"(eiro|eira|iño|iña|ciño|ciña|mente|ito|ita)", self.entrada):
            self.entrada2 = self.entrada
            for pat, repl in [
                (r"eiros?$", "o"), (r"iños?$", "o"), (r"itos?$", "o"),
                (r"eiras?$", "a"), (r"iñas?$", "a"), (r"itas?$", "a"), (r"mente$", "")
            ]:
                self.entrada2 = sub(pat, repl, self.entrada2)

        self._load_lemma_if_plural()

        if self.palavra in self.shared.lista_x:
            self.palavra = sub(r"x", "ks", self.palavra)
        if self.palavra in self.shared.lista_2x:
            self.palavra = sub(r"x([^x]+)x", r"ks\1S", self.palavra)

        self.palavra = sub(r"^cee$", "cé", self.palavra)
        self.palavra = sub(r"(^|[^cn])h", r"\1", self.palavra)
        self.palavra = sub(r"ss", "s", self.palavra)
        self.palavra = sub(r"ck", "k", self.palavra)
        self.palavra = sub(r"ff", "f", self.palavra)
        self.palavra = sub(r"pp", "p", self.palavra)

        if search(r"unha", self.palavra):
            self.palavra = sub(r"algunha", "alguNa", self.palavra)
            self.palavra = sub(r"ningunha", "ninguNa", self.palavra)
            self.palavra = sub(r"^([dnc]?)unha(s)?$", r"\1uNa\2", self.palavra)
        elif search(r"nh", self.palavra):
            self.palavra = sub(r"nh", "n", self.palavra)

        self.palavra = self.palavra.replace("kiwi", "kivi").replace("kuwait", "kuvait")
        for pat, repl in [
            (r"v", "b"), (r"gu(e|é|i|í)", r"g\1"), (r"qu", "k"), (r"ü(e|é|i|í)", r"u\1"),
            (r"ch", "tS"), (r"c(e|é|i|í)", r"T\1"), (r"c", "k"), (r"z", "T"), (r"ll", "L"),
            (r"ñ", "J"), (r"rr", "R"), (r"^r", "R"), (r"(n|m|l|s)r", r"\1R"),
#            (r"m([^aeiouáéíóúw])?$", r"n\1"), (r"m([^aeiouáéíóúw])", r"n\1"),
            (r"x$", "ks"), (r"x([ptkcbdgTfs])", r"ks\1"), (r"x", "S"), (r"y", "j")
        ]:
            self.palavra = sub(pat, repl, self.palavra)

        if search(r"[kg]u[ao]", self.palavra):
            self.palavra = sub(r"([kg])u([ao])", r"\1w\2", self.palavra)
        if search(r"[kg]u(ou|ei|ai|au|oi)", self.palavra):
            self.palavra = sub(r"ku(ou|ei|ai|au|oi)", r"kw\1", self.palavra)
            self.palavra = sub(r"gu(ou|ei|ai|au|oi)", r"gw\1", self.palavra)

        if self.entrada == "elixir2":
            self.palavra = "eliksir"
        if search(r"2$", self.palavra):
            self.palavra = sub(r"2$", "", self.palavra)

        self._check_digits()
        self._common_syllable_markup(dip, nc, dig, atc, ats, cd, cdc, br_words, bl_words)
        self._split_syllables_and_stress_ilg(aton)
        self._apply_vowel_lookups(self.shared)
        deep = self._maybe_return_deep()
        if deep is not None:
            return deep
        return self._finalize_output()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Python port of silaba_0.2.pl", add_help=False)
    parser.add_argument("--help", action="help", help="show this help message and exit")
    ortho = parser.add_mutually_exclusive_group(required=True)
    ortho.add_argument("-l", action="store_true", help="Portuguese orthography")
    ortho.add_argument("-i", action="store_true", help="ILG/RAG orthography")

    out = parser.add_mutually_exclusive_group(required=True)
    out.add_argument("-d", action="store_true", help="Show phonological representation")
    out.add_argument("-p", action="store_true", help="Show phonetic transcription")
    out.add_argument("-s", action="store_true", help="Show syllabic transcription")

    parser.add_argument("-c", action="store_true", help="Complex codas")
    parser.add_argument("-t", action="store_true", help="Thetacism")
    parser.add_argument("-r", action="store_true", help="Rotacism")
    parser.add_argument("-h", action="store_true", help="Gheada")
    parser.add_argument("-b", action="store_true", help="Broad transcription")
    parser.add_argument("word")
    args = parser.parse_args(argv)

    if args.d and (args.p or args.s or args.c or args.r or args.h or args.b):
        parser.error("-d cannot be combined with -p/-s/-c/-r/-h/-b")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = Silaba(args).run(args.word)
    except SilabaError as exc:
        print(str(exc))
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
