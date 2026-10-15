"""Terminal queue manager for a Banco Meridional branch.

Each service type has its own queue, so an agent can call the next client
for their service without scanning clients waiting for other services.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime

SERVICE_TYPES = ("deposit", "withdrawal", "account_management")


class EmptyQueueError(LookupError):
    """Raised when an agent calls or peeks a service that has no clients."""


@dataclass(frozen=True)
class Ticket:
    """A numbered ticket issued to one client for one service."""

    number: int
    client_name: str
    service_type: str
    issued_at: datetime

    def __str__(self) -> str:
        issued = self.issued_at.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"#{self.number} {self.client_name} "
            f"({self.service_type}, issued {issued})"
        )


class BranchQueue:
    """One FIFO queue per service type, plus a branch-wide ticket counter."""

    def __init__(self) -> None:
        self._queues: dict[str, deque[Ticket]] = {
            service: deque() for service in SERVICE_TYPES
        }
        self._next_number = 1

    def issue_ticket(self, client_name: str, service_type: str) -> Ticket:
        """Register a client in the queue for their service and return the ticket."""
        name = client_name.strip()
        if not name:
            raise ValueError("Client name cannot be empty.")
        service = self._require_service(service_type)

        ticket = Ticket(
            number=self._next_number,
            client_name=name,
            service_type=service,
            issued_at=datetime.now(),
        )
        self._queues[service].append(ticket)
        self._next_number += 1
        return ticket

    def call_next(self, service_type: str) -> Ticket:
        """Remove and return the client who has waited longest for this service.

        The dequeue is the first state change. See DESIGN.md for why that
        order matters when two agents call the same service together.
        """
        service = self._require_service(service_type)
        queue = self._queues[service]
        if not queue:
            raise EmptyQueueError(f"No clients are waiting for {service}.")
        return queue.popleft()

    def peek_next(self, service_type: str) -> Ticket:
        """Return the next client for this service without removing them."""
        service = self._require_service(service_type)
        queue = self._queues[service]
        if not queue:
            raise EmptyQueueError(f"No clients are waiting for {service}.")
        return queue[0]

    def list_waiting(self) -> dict[str, list[Ticket]]:
        """Return waiting tickets grouped by service, in the order they will be called."""
        return {service: list(queue) for service, queue in self._queues.items()}

    def stats(self) -> dict[str, int]:
        """Return the waiting count per service type and an overall total."""
        counts = {service: len(queue) for service, queue in self._queues.items()}
        counts["total"] = sum(counts.values())
        return counts

    def _require_service(self, service_type: str) -> str:
        service = service_type.strip().lower()
        if service not in self._queues:
            allowed = ", ".join(SERVICE_TYPES)
            raise ValueError(
                f"Unknown service type '{service_type}'. Expected one of: {allowed}."
            )
        return service


def _prompt_service() -> str:
    allowed = ", ".join(SERVICE_TYPES)
    return input(f"Service type ({allowed}): ")


def _print_waiting(waiting: dict[str, list[Ticket]]) -> None:
    for service, tickets in waiting.items():
        print(f"\n{service} ({len(tickets)} waiting)")
        if not tickets:
            print("  (none)")
            continue
        for ticket in tickets:
            print(f"  {ticket}")


def _print_stats(counts: dict[str, int]) -> None:
    print()
    for service in SERVICE_TYPES:
        print(f"  {service}: {counts[service]}")
    print(f"  total: {counts['total']}")


def main() -> None:
    """Run the branch terminal menu until the user exits."""
    branch = BranchQueue()
    menu = """
Banco Meridional — branch queue
1. Issue a ticket
2. Call next client
3. View waiting list
4. View stats
5. Exit
"""
    while True:
        print(menu)
        try:
            choice = input("Choose an option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        try:
            if choice == "1":
                name = input("Client name: ")
                service = _prompt_service()
                ticket = branch.issue_ticket(name, service)
                print(f"Issued {ticket}")
            elif choice == "2":
                service = _prompt_service()
                ticket = branch.call_next(service)
                print(f"Now serving {ticket}")
            elif choice == "3":
                _print_waiting(branch.list_waiting())
            elif choice == "4":
                _print_stats(branch.stats())
            elif choice == "5":
                print("Exiting.")
                return
            else:
                print("Please choose 1, 2, 3, 4, or 5.")
        except (ValueError, EmptyQueueError) as error:
            print(error)
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return


if __name__ == "__main__":
    main()
