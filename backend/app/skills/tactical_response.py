"""Converte resultados auditáveis do motor em uma resposta de chat."""
class TacticalResponse:
    def format(self, report: dict) -> dict:
        report["answer"] += "\n\n**Alternativas:** " + (
            " | ".join(
                f"{item['title']} ({item['main_actions']} ações principais)"
                for item in report["alternatives"][1:3]
            ) if len(report["alternatives"]) > 1 else "Nenhuma alternativa validada."
        )
        return report
