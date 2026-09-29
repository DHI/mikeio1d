# Glossary: `mikeio1d.network`

The words the network module's API and docs use, and what each one means.

**Location**
: A place in a network where series can be read: a model node, or a breakpoint along a reach.

**Address**
: A location under the name its model gave it. A `str` is a model node's id. A
  `(reach_id, position)` tuple is a breakpoint. `Network.addresses()` lists them, and
  `Network.read()` takes them.

**`Location`**
: What `Network.resolve(address)` answers for an address it has: the address as the
  network spells it, the quantities it carries, and its graph node.

**Model node**
: A node as the model has it (a manhole, a junction, a tank), named by its id. "Node" on
  its own always means a model node.

**Graph node**
: The integer that labels a location in `Network.to_networkx()`. Every location has one, a
  breakpoint too. `Location.graph_node` gives it, `to_dataset()` is indexed by it, and
  `graph.nodes[graph_node]["address"]` turns it back into the address.

**Reach**
: A directed connection between two model nodes, with the breakpoints along it.

**Structure reach**
: The reach a weir, pump or other structure sits on. Its id keeps the type prefix the
  result file gives it (`Weir:119w1`, `Pump:115p1`), while `Res1D.structures` uses the bare
  id (`119w1`). The prefix keeps apart a weir and a pump that share an id.

**Gridpoint**
: The result file's own term for a computational point on a reach. Each one the network
  keeps becomes a breakpoint.

**Breakpoint**
: A location along a reach, between its two end nodes: the network's name for a gridpoint.
  A reach's end nodes are not breakpoints: they are model nodes, named by their ids.

**Position**
: Where a breakpoint sits along its reach, in the reach's own frame: a place, not a size.
  It is not always measured from the start node: a MIKE river reach reports its chainage
  along the whole branch, which can begin far from zero, or below it.
  `NetworkReach.start_position` is where the start node sits in that frame.

**Length**
: A size: a reach's `length`, or an edge's, the distance between two positions. `None`
  where it is not known, as for an EPANET pump or valve.

**Quantity**
: A variable a result file holds, by its id (`WaterLevel`, `Discharge`).

**Carries**
: A location carries a quantity when the result file holds that quantity's series there.
  A location can carry nothing of its own (a MIKE 11 node, for example). `resolve()` still
  finds it, and `read()` refuses it.

**Item**
: An `(address, quantity)` pair: one series to read. `read()` takes a sequence of them and
  labels its columns with them.

**Companion**
: A file read alongside an EPANET result: a `.resx` with extra results for the same run.
  `Network.open` looks for it beside the result file unless told otherwise. The `.inp`
  input file is not one: the `.res` holds the reach lengths too.
