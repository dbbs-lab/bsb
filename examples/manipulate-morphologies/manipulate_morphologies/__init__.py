import os


def templates():  # pragma: nocover
    """
    :meta private:
    """
    return [os.path.abspath(os.path.dirname(os.path.dirname(__file__)))]


classmap = {
    "bsb.placement.distributor.MorphologyGenerator": {
        "touchdown": "manipulate_morphologies.morphology_generator.TouchTheBottomMorphologies",
    },
    "bsb.placement.distributor.MorphologyDistributor": {
        "small_top": "manipulate_morphologies.space_aware_morphology_distributor.SmallerTopMorphologies",
    },
}
