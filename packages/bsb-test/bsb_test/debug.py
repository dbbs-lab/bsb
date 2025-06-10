from bsb import ConnectionStrategy, config, types


@config.node
class FixedConnectivity(ConnectionStrategy):
    connections = config.attr(type=types.ndarray(), required=True)

    def queue(self, pool):
        pool.queue_connectivity(self, [], [])

    def connect(self, presyn_collection, postsyn_collection):
        for pre_type in self.presynaptic.cell_types:
            for post_type in self.postsynaptic.cell_types:
                cs = self.scaffold.require_connectivity_set(pre_type, post_type)
                cs.connect(
                    pre_type.get_placement_set(),
                    post_type.get_placement_set(),
                    self.connections[:, :3],
                    self.connections[:, 3:],
                )
