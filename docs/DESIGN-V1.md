# Design document

## Specification

Provided as input IRDL dialects and PDL patterns, the purpose of the generated chip is to match the patterns on a stream of encoded operations of the provided dialects. The chip outputs the amount of successful matches.

Dialects must satisfy the following constraints:

- No operation should contain a region.
- No operation should bear attributes.
- All operations should have at most one result.
- All operations should have a finite amount of operands, with no variadics.
- All operands and result must be of a fixed type.

Only PDL-Interp patterns that do not get the users of operations and do not use functions are supported.

A bound `N` must be chosen, and any DAG spanning more than `N` instructions will not be matched.

## Stream

The stream is a sequence of encoded operations contained in blocks. The operations of a block are streamed starting from its end up to its first operation, followed by virtual operations representing the block arguments. Blocks are separated by block identifiers, specifying the ID of the block that was just processed.

## Matcher unit

A matcher is a unit taking the stream as input and attempting to match its associated pattern. It is composed of three parts:

- The gatherer. This part receives an operation from the stream on every clock cycle, and will use it to fill the DAG buffer accordingly.
- The DAG buffer. This is a buffer shaped as a specific operation DAG instance, which can contain all possible DAGs the pattern can match.
- The pattern FSM. This part runs the PDL-Interp state machine of the associated pattern, obtaining data from the DAG buffer.

The DAG buffer acts as a memory of the operations relevant to the FSM. It gets filled with all the operations the FSM could possibly reach, so the FSM can address it directly.

### DAG Buffer

#### Rationale

Precisely, a DAG (in the sense of a DAG buffer) is a directed acyclic graph of uses rooted in the operation currently attempting to be matched on a pattern. An edge in this graph represents a use, where `A -> B` means that A uses B. PDL patterns describe how to match such graphs, rooted at a given operation.

The *structure* of a DAG is its graph node and edge structure, ignoring which operations exactly are matched. For example, the structure of the simple DAG `Op1 -> Op2 -> Op3` is `o -> o -> o`. A PDL pattern under the hypothesis of the chip can match a finite amount of DAGs with different structures. By taking the union `U` of those structures, we can describe the minimal graph structure such that the structure of all matched DAGs is a substructure of `U`. To prevent conflicts in case of unindentical operations where one was expected, the DAG must be unfolded into a tree.

The DAG buffer is a set of operation registers structured in the shape of `U`. Given a root operation, the gatherer part of the matcher fills the DAG buffer with the corresponding operations from the stream. Because `U` contains all matchable structures, the pattern FSM can decide if a DAG is matched from knowledge of only the operations gathered in the DAG buffer.

Thanks to the structure of the DAG buffer, the FSM can statically address elements of the structure it is trying to match, side-stepping the need for random-access memory.

#### Registers

Each node of the DAG buffer structure is a register that can store an operation. As operations are progressively filled by scanning the stream, the content of those registers may change over time.

Registers have three states in which they contain different data. This is modeled as a sum type with the following variants:

- `Unknown` is the default state. It represents the case when an operation has not been found and is not scheduled to be filled yet.
- `LocatedAt(int)` is set once we know where in the stream relative to the current operation the operation will be located. This is filled in once the user of this node has been found.
- `Found(Operation, int)` is set once the operation is found. The second integer operation is the offset relative to the root operation, used to disambiguate identical operations.
- `Never` is set if the parent operation does not have this branch of the DAG structure.

The gatherer applies the following procedure to fill the DAG buffer:

- Fill in the root register with `Found(root_op)`
- `counter = 0`
- For each incoming operation `op`:
    - `counter += 1`
    - For each register `r` in the buffer:
        - If `r` is `LocatedAt(0)`:
            - Set `r` to `Found(op, counter)`
            - Set the children of `r` in the DAG buffer to `LocatedAt(x)` where `x` is the relative position of the operand operation in `op`, or to `Never` if `op` does not have this operand.
        - If `r` is `LocatedAt(n)` for any non-zero `n`:
            - Set `r` to `LocatedAt(n-1)`
        - If `r` is `Never`:
            - Set the children of `r` to `Never`

An `Operation` instance contains the following data:

- The type ID of the operation.
- Whether or not this operation has a result.
- The list of operands, each containing:
    - The offset from the current operation where the definition of the operand lives.
    - The type ID of the operand value.

The actual structure of `Operation` may depend on usage. If it has been analyzed that some aspect of an operation will not be used by the pattern FSM, it may be omitted from the final representation.

### Instances on the chip

The chip is composed of `N` matcher units. Each matcher `n` will attempt to match operation `Ni+n` for `i` a positive integer. Physically, they are chained together to analyze the stream in parallel, one matcher passing over its current op to the next matcher. As matchers do not block the stream, the throughput should be quite high.

This approach has the nice benefit of having the latency of up to two matchers, no matter how many matchers are put in. 

A drawback of this approach is that a DAG should not span for longer than `N` both in operation locations and amount of clock cycles to execute. Mitigations can be attempted as follow:

- For the spatial bounds, this is not easy. The software stream encoder could accomodate this by placing a bound on the distance between transitive uses (making sure the distances are "well balanced"), and fall back to software when it is not. For `N` sufficiently big, one can hope the fallback would only be required in degenerate cases.
- For the time bounds, the theoretical maximum amount of cycles to analyze all DAG structures can be computed at hardware generation time, helping with the choice of `N`. The hardware should support blocking the stream to let the FSMs more time to think, if for some reason that bound is broken. (TODO: while this would get us further away from the rewriting goal, maybe not chaining the streams and having each unit walk over the stream at its own rhythm could help?)

Another drawback is that once rewriting will be considered, this wil have to change significantly to not destroy performance.

### Description as a HwModule

The structure of a matcher unit is produced as a CIRCT HwModule.

The module has the following inputs:

- clock (`i1`): represents the usual clock ticking signal.
- next_op (`HwOperation`): represents the next operation in the stream, which has been passed on by the previous matcher unit.
- is_stream_paused (`i1`): informs the matcher unit that there is currently no operation available as input, and that any output operation will not be passed over to the next matcher unit. This is useful both to wait for the first operations and to block the stream if the FSM is running late.
- new_sequence (`i1`): informs the matcher unit that the current operation should be the root of a new matching attempt.
- stream_completed (`i1`): informs the matcher unit that the current operation will be the last for this matching attempt and that the stream will be paused afterwards until the match ends. This is useful to set all not-found filler registers to `Never` to make the state machine converge.

The module has the following outputs:

- output_op (`HwOperation`): represents the operation to be passed on to the next matcher unit.
- match_result (`Unknown | Success | Failure`): state of the matching attempt, is unknown then either success or failure, until a new sequence begins. This can be used by a controller to schedule the next matching sequence or block the stream if result is late.
