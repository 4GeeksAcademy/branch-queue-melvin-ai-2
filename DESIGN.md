# Design notes

## Why one queue per service

A single list of every waiting client, ordered by arrival, forces `call_next` to scan that list until it finds the first client whose service matches the agent. That scan grows with the whole waiting room, including people the agent is not allowed to serve.

`BranchQueue` keeps a separate `collections.deque` for `deposit`, `withdrawal`, and `account_management`. A client is appended to the deque for their service only. `call_next` is then `popleft` on that deque: constant time, and independent of how many people are waiting for the other services. Arrival order inside a service is the deque order, so FIFO does not require a search.

Ticket numbers stay globally sequential because one counter on `BranchQueue` is incremented for every successful issue, no matter which deque receives the ticket.

## Two agents calling `call_next` at the same moment

If two agents for the same service both look at the front of the queue and only later remove that client, both can observe the same ticket and call the same person.

The first state change in `call_next` has to be the removal itself (`deque.popleft`). Once that removal has happened, the ticket is no longer at the front, so the other agent’s `call_next` either receives the following client or finds the queue empty. Reading the front and removing it afterward is the mutation order that allows a double call. Dequeue first, then return the ticket that was removed.
