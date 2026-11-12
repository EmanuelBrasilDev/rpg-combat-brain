"""SheetTargetResolverSkill — identifica a ficha solicitada, nunca troca pelo Akira.

Resolver nomes de personagens de combate E adversários salvos no Enemy Forge.
A referência "no mesmo modelo do Akira" descreve FORMATO, não o alvo.
Falhas e ambiguidades devem ser comunicadas; nunca retornar outra ficha.
"""
import re
import unicodedata
from dataclasses import dataclass


def _norm(value: str) -> str:
    simplified = "".join(
        ch for ch in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(ch)
    )
    return re.sub(r"\s+", " ", simplified).strip()


def _aliases(record: dict, source: str) -> list[str]:
    name = _norm(record["name"])
    aliases = [name]
    if source in ("lab", "combat"):
        # Enemy Forge cria "Guardião de Pedra · D3/S42"; cópias adotadas também
        # A parte antes do sufixo também é pesquisável, mas pode ser ambígua.
        base = re.sub(r"\s*[·•]\s*d\d+/s\d+$", "", name)
        if base != name:
            aliases.append(base)
    if record["id"] == "akira":
        aliases.append("akira")
    return aliases


@dataclass(frozen=True)
class SheetResolution:
    source: str  # combat, lab, not_found, ambiguous
    record: dict | None = None
    message: str = ""


class SheetTargetResolverSkill:
    """Resolução pura: nenhuma leitura, criação ou atualização de ficha."""

    def resolve(self, message: str, selected_id: str, characters: list[dict],
                lab_enemies: list[dict]) -> SheetResolution:
        normalized = _norm(message)
        records = [("combat", sheet) for sheet in characters] + [
            ("lab", profile) for profile in lab_enemies
        ]
        command = re.fullmatch(r"/ficha-texto(?:\s+(.*))?", normalized)
        if command:
            argument = (command.group(1) or "").strip()
            if not argument:
                sheet = next((c for c in characters if c["id"] == selected_id), None)
                if sheet:
                    return SheetResolution("combat", sheet)
                return SheetResolution("not_found", message="Selecione uma ficha de combate válida.")
            # IDs sempre têm prioridade; permitem desambiguar gerações do mesmo nome.
            id_matches = [(source, record) for source, record in records
                          if _norm(record["id"]) == argument
                          or (source == "lab" and "lab:" + _norm(record["id"]) == argument)]
            if len(id_matches) == 1:
                source, record = id_matches[0]
                return SheetResolution(source, record)
            # /ficha-texto Guardião de Pedra também funciona como nome.
            return self._choose_name(argument, records, explicit_command=True)

        return self._choose_name(normalized, records, selected_id=selected_id)

    def _choose_name(self, normalized: str, records: list[tuple[str, dict]],
                     selected_id: str | None = None,
                     explicit_command: bool = False) -> SheetResolution:
        candidates: list[dict] = []
        for source, record in records:
            best = None
            for alias in _aliases(record, source):
                if not alias:
                    continue
                for found in re.finditer(
                    r"(?<!\w)" + re.escape(alias) + r"(?!\w)", normalized
                ):
                    prefix = normalized[max(0, found.start() - 65):found.start()]
                    # "no mesmo modelo do Akira" não quer dizer exportar Akira.
                    style_ref = bool(re.search(
                        r"\b(?:modelo|estilo|formato|padrao|igual|como)\b"
                        r"[^.!?\n]{0,35}\b(?:do|da|de)\s+$", prefix
                    ))
                    # "ficha do Guardião", "ficha estilizada do Guardião", etc.
                    subject_ref = bool(re.search(
                        r"\bficha\b(?:\s+(?!do\b|da\b|de\b)[\w-]+){0,3}"
                        r"\s+(?:do|da|de)\s+$", prefix
                    )) and not style_ref
                    match = {
                        "source": source, "record": record,
                        "full": len(alias) == len(_norm(record["name"])),
                        "length": len(alias), "subject": subject_ref,
                        "style": style_ref,
                        "position": found.start(),
                    }
                    if best is None or (
                        int(match["subject"]), int(not match["style"]),
                        int(match["full"]), match["length"]
                    ) > (
                        int(best["subject"]), int(not best["style"]),
                        int(best["full"]), best["length"]
                    ):
                        best = match
            if best is not None:
                candidates.append(best)

        subjects = [c for c in candidates if c["subject"]]
        if subjects:
            candidates = subjects
        else:
            candidates = [c for c in candidates if not c["style"]]

        if not candidates:
            if not explicit_command:
                if re.search(
                    r"\b(?:essa|esta|aquela|dessa|daquela)\s+ficha\b|"
                    r"\bficha\s+(?:que\s+)?(?:voce\s+)?(?:criou|gerou|gerada|criada)\b",
                    normalized,
                ):
                    return SheetResolution(
                        "ambiguous",
                        message=(
                            "Você pediu 'essa ficha', mas não há uma ficha-alvo "
                            "identificada no chat. Informe o nome, como "
                            "'Guardião de Pedra', ou use /ficha-texto <id>. "
                            "Não vou substituir por Akira."
                        )
                    )
                # Uma referência explícita a uma ficha DESCONHECIDA não pode
                # fazer fallback silencioso para o Akira selecionado.
                named_request = re.search(
                    r"\bficha\b[^.!?\n]{0,45}\b(?:do|da|de)\s+\w+", normalized
                )
                if not named_request:
                    # Se o usuário não citou ninguém, o alvo é o selecionado.
                    active = next((c for c in (r for s, r in records if s == "combat")
                                   if c["id"] == selected_id), None)
                    if active:
                        return SheetResolution("combat", active)
            return SheetResolution(
                "not_found",
                message=(
                    "Não encontrei a ficha solicitada entre os combatentes ou "
                    "adversários salvos no Enemy Forge. Confira o nome exato ou "
                    "use /ficha-texto <id>."
                )
            )

        # Menções completas têm precedência sobre prefixos de outras gerações.
        if any(c["full"] for c in candidates):
            candidates = [c for c in candidates if c["full"]]
        # Se a mesma ficha já foi adotada no combate, preferir a cópia EDITÁVEL
        # de combate. Outras gerações com mesma raiz continuam ambíguas.
        combat_matches = [c for c in candidates if c["source"] == "combat"]
        if combat_matches:
            candidates = combat_matches
        if len(candidates) == 1:
            item = candidates[0]
            return SheetResolution(item["source"], item["record"])
        options = "; ".join(
            f"{c['record']['name']} (ID {c['record']['id']}, "
            f"{'combate' if c['source'] == 'combat' else 'laboratório'})"
            for c in candidates[:8]
        )
        return SheetResolution(
            "ambiguous",
            message=(
                "Há mais de uma ficha compatível. Qual delas deseja exportar? "
                + options + ". Use /ficha-texto <id> para selecionar exatamente uma."
            )
        )
