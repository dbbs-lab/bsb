import os


def templates():  # pragma: nocover
    """
    :meta private:
    """
    return [os.path.abspath(os.path.dirname(os.path.dirname(__file__)))]


classmap = {
    "bsb.postprocessing.AfterPlacementHook": {
        "label_cell": "cell_labeling.label_cells.LabelCellA",
    },
}
