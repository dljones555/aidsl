AI KERNEL SPEC v0.1
Author: DLJ — Vision & Architecture
Implementation Target: Rust core, Python/DSL bindings

PRIMITIVES REQUIRED:

Loop scheduler
    - do_while: condition-driven, preemptible
    - do_until: goal-directed, metric-tracked, 
                stagnation-detected
    - meta_loop: OODA, fires on stagnation signal
                 from child loops
    - Safety: MAX_LOOP_TURNS enforced at scheduler 
              level, not application level

State manager  
    - Checkpoint at every node transition
    - Resume from checkpoint after failure
    - Durable across process boundaries
    - TTL-aware: loop state expires correctly
    - Tenant-isolated: no state bleed between 
                       execution contexts

Signal system
    - HITL signal: async, arbitrary duration,
                   typed payload, loop suspension
                   and resumption
    - PEER signal: typed inter-loop message passing
    - SAFETY signal: preempts any loop immediately,
                     non-maskable
    - METRIC signal: delta threshold crossed,
                     propagates up to meta_loop

Metric tracker
    - Per-loop metric registration
    - Delta computation per turn
    - Threshold comparison
    - Stagnation detection: delta below threshold
                            for N consecutive turns
    - Aggregation across loop hierarchy

Safety verifier
    - LTL property checking at compile time
    - Execution path enumeration
    - Invariant verification before deployment
    - Runtime enforcement as second layer

Compute scheduler
    - GPU allocation per loop
    - CPU allocation per rule execution
    - Human time estimation per HITL node
    - Budget enforcement: hard stop at limit
    - Cost attribution per loop, per tenant

Loop registry
    - Named loop patterns
    - Loop lifecycle: spawn, run, suspend,
                      resume, terminate, reap
    - Parent-child relationships for meta loops
    - Distributed: loops can migrate across nodes

**Session prompt that gets above started**

You are implementing the core runtime kernel for 
an AI execution system. Think like a systems 
programmer. Correctness before features. 
Memory safety guaranteed. No garbage collection 
pauses in hot paths. Async-first throughout.

Your first task: implement the Loop struct with 
do_while, do_until, and meta_loop variants as 
a Rust enum with associated state. Each variant 
has different termination semantics. Start there.
Do not build anything else until this is correct.

Reference: [paste kernel spec above]