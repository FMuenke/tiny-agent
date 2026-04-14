"""Swarm orchestrator — Chat → Broker → Executor."""

from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from clawlite.agents import ChatAgent, Executor, SkillBroker
from clawlite.ollama_client import OllamaClient

console = Console()


class Orchestrator:
    """Coordinates ChatAgent, SkillBroker, and Executor."""

    def __init__(
        self,
        model: str = "gemma4:e4b",
        max_steps: int = 10,
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.client = OllamaClient(base_url=base_url, model=model)
        self.chat = ChatAgent(self.client)
        self.broker = SkillBroker(self.client)
        self.executor = Executor(self.client, max_steps=max_steps)

    def run(self, user_input: str) -> str:
        if not self.client.check_health():
            return (
                f"❌ **Cannot reach Ollama or model `{self.model}` missing.**\n\n"
                f"1. `ollama serve`\n2. `ollama pull {self.model}`"
            )

        with Live(
            Panel("💬 ChatAgent thinking...", title="ClawLite", border_style="blue"),
            refresh_per_second=4,
        ) as live:

            def update(title: str, body: str, style: str = "blue") -> None:
                live.update(Panel(body, title=f"ClawLite · {title}", border_style=style))

            try:
                # 1. ChatAgent: reply or dispatch?
                update("ChatAgent", "Deciding whether to reply or dispatch...", "blue")
                decision = self.chat.decide(user_input)

                action = decision.get("action")
                if action == "reply":
                    return decision.get("text", "")

                if action != "execute":
                    return (
                        f"❌ **ChatAgent returned unknown action** `{action}`.\n\n"
                        f"Raw: {decision}"
                    )

                intent = decision.get("intent", "").strip()
                if not intent:
                    return "❌ **ChatAgent dispatched an empty intent.**"

                # 2. Broker: pick skills
                update("Broker", f"Selecting skills for: {intent}", "yellow")
                skills = self.broker.select(intent)
                if not skills:
                    return (
                        f"❌ **Broker selected no skills** for intent:\n> {intent}"
                    )

                update(
                    "Broker",
                    f"Intent: {intent}\nSkills: {', '.join(skills)}",
                    "yellow",
                )

                # 3. Executor: run the tool loop
                def exec_status(stage: str, detail: str) -> None:
                    update(
                        f"Executor · {stage}",
                        f"Intent: {intent}\nSkills: {', '.join(skills)}\n\n{detail}",
                        "green",
                    )

                return self.executor.run(intent, skills, status=exec_status)

            except KeyboardInterrupt:
                return "\n\n⏸️ **Interrupted by user**"
            except Exception as e:
                return f"❌ **Orchestrator error**: {e}"
