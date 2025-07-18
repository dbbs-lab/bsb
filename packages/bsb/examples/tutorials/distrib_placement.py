import numpy as np

from bsb import PlacementStrategy, config, types


@config.node
class DistributionPlacement(PlacementStrategy):
    """
    Place cells based on a scipy distribution along a specified axis.
    """

    distribution = config.attr(type=types.distribution(), required=True)
    """Scipy distribution to apply to the cell coordinate along the axis"""
    axis: int = config.attr(type=types.int(min=0, max=2), required=False, default=2)
    """Axis along which to apply the distribution (i.e. x, y or z)"""
    direction: str = config.attr(
        type=types.in_(["positive", "negative"]), required=False, default="positive"
    )
    """Specify if the distribution is applied along positive or negative axis direction"""

    def draw_interval(self, n, lower, upper):
        """
        Apply an acceptance-rejection method to n points according to the provided
        interval of the distribution.
        This method draws n random values and returns the number which value is
        less than the probability to fall in the provided interval boundaries.

        :param int n: Number of points to draw
        :param float lower: Lower bound of the interval within [0, 1]
        :param float upper: Upper bound of the interval within [0, 1]
        :return: Number of points passing the acceptance-rejection test.
        :rtype: int
        """
        # Extract the interval of values that can be generated by the distribution
        # Since some distribution values can reach infinite, we clamp the interval
        # so that the probability to be out of this interval is 1e-9
        distrib_interval = self.distribution.definition_interval(1e-9)
        # Retrieve the value at the lower and upper bound ratios of the
        # distribution's interval
        value_upper = upper * np.diff(distrib_interval) + distrib_interval[0]
        value_lower = lower * np.diff(distrib_interval) + distrib_interval[0]
        # Retrieve the probability of a value to be lower than the upper value
        selected_lt = self.distribution.cdf(value_upper)
        # Retrieve the probability of a value to be greater than the lower value
        selected_gt = self.distribution.sf(value_lower)
        # Apply the acceptance-rejection method: a random point within [0,1] is
        # accepted if it is lower than the probability to be less than the upper
        # value and the probability to be greater than the lower value
        random_numbers = np.random.rand(n)
        selected = random_numbers <= selected_lt * selected_gt
        # Returns the number of point passing the test
        return np.count_nonzero(selected)

    def place(self, chunk, indicators):
        # For each placement indicator
        for _name_indic, indicator in indicators.items():
            # Prepare an array to store positions
            all_positions = np.empty((0, 3))
            # For each partitions
            for p in indicator.partitions:
                # Guess the number of cells to place within the partition.
                num_to_place = indicator.guess(voxels=p.to_voxels())
                # Extract the size of the partition
                partition_size = p._data.mdc - p._data.ldc
                # Retrieve the ratio interval occupied by the current Chunk along the axis
                chunk_borders = np.array([chunk.ldc, chunk.mdc])
                ratios = (chunk_borders - p._data.ldc) / partition_size
                bounds = ratios[:, self.axis]
                if self.direction == "negative":
                    # If the direction on which to apply the distribution is inverted,
                    # then the ratio interval should be inverted too.
                    bounds = 1 - bounds
                    bounds = bounds[::-1]

                # Draw according to the distribution the random number of cells to
                # place in the Chunk
                num_selected = self.draw_interval(
                    num_to_place, lower=bounds[0], upper=bounds[1]
                )
                # ratio of area occupied by the chunk along the two other dimensions
                ratio_area = np.diff(np.delete(ratios, self.axis, axis=1), axis=0)
                num_selected *= np.prod(ratio_area)
                if num_selected > 0:
                    # Assign a random position to the cells within this Chunk
                    positions = (
                        np.random.rand(num_selected, 3) * chunk.dimensions + chunk.ldc
                    )
                    all_positions = np.concatenate([all_positions, positions])
            self.place_cells(indicator, all_positions, chunk)
