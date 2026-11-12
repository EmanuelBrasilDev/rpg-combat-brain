"""EnemyForgeSkill: adversários reproduzíveis; nunca transforma invenção em cânone."""
import random
import uuid
from ..lab_models import EnemyProfile, EnemyTechnique, GenerateEnemyRequest

# Blocos são explicitamente FICTÍCIOS e só existem em cenários de teste.
TECHNIQUE_LIBRARY: dict[str, list[tuple[str, str, str]]] = {
    "assault": [
        ("Talho Crescente", "golpe físico com pressão", "physical"),
        ("Avanço Corrompido", "ataque de avanço", "physical"),
        ("Rajada de Energia", "projetil à distância", "technique"),
        ("Investida Brutal", "ataque direto", "physical"),
        ("Explosão Ruptora", "dano em área (hipotético)", "technique"),
    ],
    "defense": [
        ("Escudo Rochoso", "postura de bloqueio; resolução ainda não implementada", "defense"),
        ("Contra-golpe Denso", "contra-ataque condicionado", "physical"),
        ("Casca Reforçada", "aumento defensivo (simulado)", "defense"),
        ("Onda de Repulsão", "empurra adversários (simulado)", "technique"),
        ("Golpe de Guarda", "ataque básico de curto alcance", "physical"),
    ],
    "control": [
        ("Correntes Sombras", "restrição de movimentação (simulada)", "control"),
        ("Marca de Lentidão", "penalidade de precisão (simulada)", "control"),
        ("Orbe de Pressão", "ataque de energia", "technique"),
        ("Zona de Interdição", "área de controle (simulada)", "control"),
        ("Fragmentos Errantes", "projeteis perseguintes (simulados)", "technique"),
    ],
    "balanced": [
        ("Corte Sombrio", "ataque físico", "physical"),
        ("Pulso Amaldiçoado", "ataque de energia", "technique"),
        ("Postura de Guarda", "bloqueio (simulado)", "defense"),
        ("Garra de Interrupção", "contra-ataque (simulado)", "physical"),
        ("Chuva de Estilhaços", "dano em área (simulado)", "technique"),
    ],
}

class EnemyForgeSkill:
    """Perfis com sementes fixas; sem dependência de LLM, web ou aleatoriedade global."""

    def generate(self, request: GenerateEnemyRequest) -> EnemyProfile:
        profile_id = str(uuid.uuid4())
        if request.template == "curse_grade_3":
            return EnemyProfile(
                id=profile_id, name="Maldição Grau 3", tier="Grau 3",
                origin="user_example", template=request.template, seed=request.seed,
                hp=300, ea=200, techniques=[
                    EnemyTechnique(name="Ataque de Garras", damage="5d8 + 3d2",
                                   status="user_provided")
                ], assumptions=[
                    "Os valores HP 300, EA 200 e dano 5d8 + 3d2 foram fornecidos pelo jogador como exemplo.",
                    "Output, Reforço, Reversa e Domínio NÃO foram informados e permanecem desconhecidos."
                ]
            )
        if request.template == "mahito_reference":
            return EnemyProfile(
                id=profile_id, name="Mahito", origin="user_example",
                template=request.template, seed=request.seed,
                hp=1000, ea=1200,
                techniques=[
                    EnemyTechnique(name=f"Técnica ({i})", cooldown=0, status="placeholder")
                    for i in range(1, 7)
                ],
                assumptions=[
                    "HP 1000 e EA 1200 são valores do exemplo do jogador, não ficha oficial verificada.",
                    "Os nomes, efeitos, custos e danos das seis técnicas NÃO foram informados.",
                    "Nenhuma técnica canônica de Mahito foi inventada; placeholders não executam ações."
                ]
            )
        return self._procedural(request, profile_id)

    def _procedural(self, request: GenerateEnemyRequest, profile_id: str) -> EnemyProfile:
        rng = random.Random(request.seed)
        difficulty, archetype = request.difficulty, request.archetype
        # Escalas ARBITRÁRIAS do laboratório. Nunca confundir com estatísticas oficiais.
        hp = int((200 + difficulty * 100) * (1.30 if archetype == "defense" else 1))
        ea = int((110 + difficulty * 90) * (1.25 if archetype == "control" else 1))
        spirit = max(1, difficulty * 2 + rng.randint(0, 4))
        dexterity = max(1, difficulty * 2 + rng.randint(0, 4))
        library = list(TECHNIQUE_LIBRARY[archetype])
        rng.shuffle(library)
        techniques: list[EnemyTechnique] = []
        for name, effect, attack_type in library[:min(5, 2 + difficulty)]:
            amount = difficulty + rng.randint(1, 3)
            sides = 8 if attack_type == "physical" else 6
            damage = f"{amount}d{sides} + {max(1, difficulty)}d2" if attack_type != "defense" else None
            techniques.append(EnemyTechnique(
                name=name, damage=damage, effect=effect,
                ea_cost=0 if attack_type == "physical" else 6 * difficulty + rng.randint(0, 10),
                cooldown=rng.randint(0, 2), status="synthetic",
                accuracy_bonus=f"{max(1, difficulty)}d2" if attack_type == "physical" else None
            ))
        domain_level = min(3, difficulty - 2) if difficulty >= 4 else 0
        if domain_level:
            techniques.append(EnemyTechnique(
                name="Domínio de Teste (hipotético)", effect="Pressão de domínio; efeitos exatos dependem de regras cadastradas.",
                ea_cost=60 + difficulty * 20, cooldown=0, status="synthetic"
            ))
        names = {
            "assault": "Predador de Cinzas", "defense": "Guardião de Pedra",
            "control": "Vigia do Vazio", "balanced": "Maldição Adaptativa"
        }
        return EnemyProfile(
            id=profile_id, name=f"{names[archetype]} · D{difficulty}/S{request.seed}",
            tier="Procedural (sem grau oficial)", origin="synthetic", template="procedural",
            archetype=archetype, difficulty=difficulty, seed=request.seed,
            hp=hp, ea=ea, spirit=spirit, dexterity=dexterity,
            reinforcement_level=min(10, max(0, difficulty - 1)),
            output_level=min(10, max(0, difficulty - 1 if archetype != "control" else difficulty)),
            reverse_level=min(10, max(0, difficulty - 2)),
            domain_level=domain_level,
            extra_metrics={
                "role": archetype, "aggression_score": min(100, 35 + 10 * difficulty),
                "is_synthetic": True
            },
            techniques=techniques,
            assumptions=[
                "FICHA SINTÉTICA: todos os valores, técnicas e graus são hipóteses de teste, não regras oficiais.",
                "Os níveis de Reforço/Output/Reversa/Domínio representam capacidades simuladas; custos/efeitos precisam de implementação.",
                "Esta geração não altera a batalha real nem treina automaticamente os pesos do agente."
            ]
        )
