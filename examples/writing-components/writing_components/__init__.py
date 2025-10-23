import os


def templates():  # pragma: nocover
    """
    :meta private:
    """
    return [os.path.abspath(os.path.dirname(os.path.dirname(__file__)))]


classmap = {
    "bsb.connectivity.strategy.ConnectionStrategy": {
        "dist_conn": "writing_components.dist_connection.DistanceConnectivity",
    },
    "bsb.placement.strategy.PlacementStrategy": {
        "distrib_placement": "writing_components.distrib_placement.DistributionPlacement",
    },
}
