"""
`bsb-core` is the backbone package contain the essential code of the BSB: A component
framework for multiscale bottom-up neural modelling.

`bsb-core` needs to be installed alongside a bundle of desired bsb plugins, some of
which are essential for `bsb-core` to function. First time users are recommended to
install the `bsb` package instead.
"""

import functools
import importlib
import sys
import typing
import warnings

import bsb.exceptions as _exc

# Patch functools on 3.8
try:
    _cache = functools.cache
except AttributeError:
    functools.cache = functools.lru_cache

    # Patch the 'register' method of `singledispatchmethod` pre python 3.10
    def _register(self, cls, method=None):  # pragma: nocover
        if hasattr(cls, "__func__"):
            cls.__annotations__ = cls.__func__.__annotations__
        return self.dispatcher.register(cls, func=method)

    functools.singledispatchmethod.register = _register


# Always show all scaffold warnings
for e in _exc.__dict__.values():
    if isinstance(e, type) and issubclass(e, Warning):
        warnings.simplefilter("always", e)

try:
    from .options import profiling as _pr
except Exception:
    pass
else:
    if _pr:
        from .profiling import activate_session

        activate_session()


def _get_annotation_submodule(name: str):
    annotation = __annotations__.get(name, None)
    if annotation:
        type_ = typing.get_args(annotation)
        if type_:
            annotation = type_[0]
        return annotation[4 : -len(name) - 1]


@functools.cache
def __getattr__(name):
    if name == "config":
        return object.__getattribute__(sys.modules[__name__], name)
    module = _get_annotation_submodule(name)
    if module is None:
        return object.__getattribute__(sys.modules[__name__], name)
    else:
        return getattr(importlib.import_module("." + module, package="bsb"), name)


@functools.cache
def __dir__():
    return [*__annotations__.keys()]


# Do not modify: autogenerated public API type annotations of the `bsb` module
# fmt: off
# isort: off
if typing.TYPE_CHECKING:
  import bsb.cell_types
  import bsb.cli
  import bsb.cli.commands
  import bsb.config
  import bsb.config.parsers
  import bsb.config.refs
  import bsb.config.types
  import bsb.connectivity.detailed.shared
  import bsb.connectivity.detailed.voxel_intersection
  import bsb.connectivity.general
  import bsb.connectivity.geometric.geometric_shapes
  import bsb.connectivity.geometric.morphology_shape_intersection
  import bsb.connectivity.geometric.shape_morphology_intersection
  import bsb.connectivity.geometric.shape_shape_intersection
  import bsb.connectivity.import_
  import bsb.connectivity.strategy
  import bsb.core
  import bsb.exceptions
  import bsb.mixins
  import bsb.morphologies
  import bsb.morphologies.parsers
  import bsb.morphologies.parsers.parser
  import bsb.morphologies.selector
  import bsb.option
  import bsb.options
  import bsb.placement.arrays
  import bsb.placement.distributor
  import bsb.placement.import_
  import bsb.placement.indicator
  import bsb.placement.random
  import bsb.placement.strategy
  import bsb.plugins
  import bsb.postprocessing
  import bsb.profiling
  import bsb.reporting
  import bsb.services
  import bsb.simulation
  import bsb.simulation.adapter
  import bsb.simulation.cell
  import bsb.simulation.component
  import bsb.simulation.connection
  import bsb.simulation.device
  import bsb.simulation.parameter
  import bsb.simulation.results
  import bsb.simulation.simulation
  import bsb.simulation.targetting
  import bsb.storage
  import bsb.storage._chunks
  import bsb.storage._files
  import bsb.storage.decorators
  import bsb.storage.interfaces
  import bsb.topology
  import bsb.topology.partition
  import bsb.topology.region
  import bsb.trees
  import bsb.voxels

AdapterError: type["bsb.exceptions.AdapterError"]
AdapterProgress: type["bsb.simulation.adapter.AdapterProgress"]
AfterConnectivityHook: type["bsb.postprocessing.AfterConnectivityHook"]
AfterPlacementHook: type["bsb.postprocessing.AfterPlacementHook"]
AllToAll: type["bsb.connectivity.general.AllToAll"]
AllenApiError: type["bsb.exceptions.AllenApiError"]
AllenStructure: type["bsb.topology.partition.AllenStructure"]
AttributeMissingError: type["bsb.exceptions.AttributeMissingError"]
BaseCommand: type["bsb.cli.commands.BaseCommand"]
BidirectionalContact: type["bsb.postprocessing.BidirectionalContact"]
BootError: type["bsb.exceptions.BootError"]
BoxTree: type["bsb.trees.BoxTree"]
BoxTreeInterface: type["bsb.trees.BoxTreeInterface"]
Branch: type["bsb.morphologies.Branch"]
BranchLocTargetting: type["bsb.simulation.targetting.BranchLocTargetting"]
BsbCommand: type["bsb.cli.commands.BsbCommand"]
BsbOption: type["bsb.option.BsbOption"]
BsbParser: type["bsb.morphologies.parsers.parser.BsbParser"]
ByIdTargetting: type["bsb.simulation.targetting.ByIdTargetting"]
ByLabelTargetting: type["bsb.simulation.targetting.ByLabelTargetting"]
CLIError: type["bsb.exceptions.CLIError"]
CLIOptionDescriptor: type["bsb.option.CLIOptionDescriptor"]
CastConfigurationError: type["bsb.exceptions.CastConfigurationError"]
CastError: type["bsb.exceptions.CastError"]
CellModel: type["bsb.simulation.cell.CellModel"]
CellModelFilter: type["bsb.simulation.targetting.CellModelFilter"]
CellModelTargetting: type["bsb.simulation.targetting.CellModelTargetting"]
CellTargetting: type["bsb.simulation.targetting.CellTargetting"]
CellType: type["bsb.cell_types.CellType"]
CfgReferenceError: type["bsb.exceptions.CfgReferenceError"]
Chunk: type["bsb.storage._chunks.Chunk"]
ChunkError: type["bsb.exceptions.ChunkError"]
CircularMorphologyError: type["bsb.exceptions.CircularMorphologyError"]
ClassError: type["bsb.exceptions.ClassError"]
ClassMapMissingError: type["bsb.exceptions.ClassMapMissingError"]
CodeDependencyNode: type["bsb.storage._files.CodeDependencyNode"]
CodeImportError: type["bsb.exceptions.CodeImportError"]
CommandError: type["bsb.exceptions.CommandError"]
CompartmentError: type["bsb.exceptions.CompartmentError"]
CompilationError: type["bsb.exceptions.CompilationError"]
Cone: type["bsb.connectivity.geometric.geometric_shapes.Cone"]
ConfigTemplateNotFoundError: type["bsb.exceptions.ConfigTemplateNotFoundError"]
Configuration: type["bsb.config.Configuration"]
ConfigurationAttribute: type["bsb.config.ConfigurationAttribute"]
ConfigurationError: type["bsb.exceptions.ConfigurationError"]
ConfigurationFormatError: type["bsb.exceptions.ConfigurationFormatError"]
ConfigurationParser: type["bsb.config.parsers.ConfigurationParser"]
ConfigurationSyncError: type["bsb.exceptions.ConfigurationSyncError"]
ConfigurationWarning: type["bsb.exceptions.ConfigurationWarning"]
ConnectionModel: type["bsb.simulation.connection.ConnectionModel"]
ConnectionStrategy: type["bsb.connectivity.strategy.ConnectionStrategy"]
ConnectionTargetting: type["bsb.simulation.targetting.ConnectionTargetting"]
ConnectivityError: type["bsb.exceptions.ConnectivityError"]
ConnectivityIterator: type["bsb.storage.interfaces.ConnectivityIterator"]
ConnectivitySet: type["bsb.storage.interfaces.ConnectivitySet"]
ConnectivityWarning: type["bsb.exceptions.ConnectivityWarning"]
ContinuityError: type["bsb.exceptions.ContinuityError"]
Convergence: type["bsb.connectivity.general.Convergence"]
CsvImportConnectivity: type["bsb.connectivity.import_.CsvImportConnectivity"]
CsvImportPlacement: type["bsb.placement.import_.CsvImportPlacement"]
Cuboid: type["bsb.connectivity.geometric.geometric_shapes.Cuboid"]
Cylinder: type["bsb.connectivity.geometric.geometric_shapes.Cylinder"]
CylindricalTargetting: type["bsb.simulation.targetting.CylindricalTargetting"]
DataNotFoundError: type["bsb.exceptions.DataNotFoundError"]
DataNotProvidedError: type["bsb.exceptions.DataNotProvidedError"]
DatasetExistsError: type["bsb.exceptions.DatasetExistsError"]
DatasetNotFoundError: type["bsb.exceptions.DatasetNotFoundError"]
DependencyError: type["bsb.exceptions.DependencyError"]
DeviceModel: type["bsb.simulation.device.DeviceModel"]
Distribution: type["bsb.config.Distribution"]
DistributionCastError: type["bsb.exceptions.DistributionCastError"]
DistributionContext: type["bsb.placement.distributor.DistributionContext"]
Distributor: type["bsb.placement.distributor.Distributor"]
DistributorError: type["bsb.exceptions.DistributorError"]
DistributorsNode: type["bsb.placement.distributor.DistributorsNode"]
DryrunError: type["bsb.exceptions.DryrunError"]
DynamicClassError: type["bsb.exceptions.DynamicClassError"]
DynamicClassInheritanceError: type["bsb.exceptions.DynamicClassInheritanceError"]
DynamicObjectNotFoundError: type["bsb.exceptions.DynamicObjectNotFoundError"]
Ellipsoid: type["bsb.connectivity.geometric.geometric_shapes.Ellipsoid"]
EmptyBranchError: type["bsb.exceptions.EmptyBranchError"]
EmptySelectionError: type["bsb.exceptions.EmptySelectionError"]
EmptyVoxelSetError: type["bsb.exceptions.EmptyVoxelSetError"]
Engine: type["bsb.storage.interfaces.Engine"]
Entities: type["bsb.placement.strategy.Entities"]
EnvOptionDescriptor: type["bsb.option.EnvOptionDescriptor"]
ExplicitNoRotations: type["bsb.placement.distributor.ExplicitNoRotations"]
ExternalSourceError: type["bsb.exceptions.ExternalSourceError"]
FileDependency: type["bsb.storage._files.FileDependency"]
FileDependencyNode: type["bsb.storage._files.FileDependencyNode"]
FileImportError: type["bsb.exceptions.FileImportError"]
FileReferenceError: type["bsb.exceptions.FileReferenceError"]
FileScheme: type["bsb.storage._files.FileScheme"]
FileStore: type["bsb.storage.interfaces.FileStore"]
FixedIndegree: type["bsb.connectivity.general.FixedIndegree"]
FixedOutdegree: type["bsb.connectivity.general.FixedOutdegree"]
FixedPositions: type["bsb.placement.strategy.FixedPositions"]
FractionFilter: type["bsb.simulation.targetting.FractionFilter"]
GatewayError: type["bsb.exceptions.GatewayError"]
GeneratedMorphology: type["bsb.storage.interfaces.GeneratedMorphology"]
GeometricShape: type["bsb.connectivity.geometric.geometric_shapes.GeometricShape"]
HasDependencies: type["bsb.mixins.HasDependencies"]
Hemitype: type["bsb.connectivity.strategy.Hemitype"]
HemitypeCollection: type["bsb.connectivity.strategy.HemitypeCollection"]
Implicit: type["bsb.placement.distributor.Implicit"]
ImplicitNoRotations: type["bsb.placement.distributor.ImplicitNoRotations"]
ImportConnectivity: type["bsb.connectivity.import_.ImportConnectivity"]
ImportPlacement: type["bsb.placement.import_.ImportPlacement"]
IncompleteExternalMapError: type["bsb.exceptions.IncompleteExternalMapError"]
IncompleteMorphologyError: type["bsb.exceptions.IncompleteMorphologyError"]
IndicatorError: type["bsb.exceptions.IndicatorError"]
InputError: type["bsb.exceptions.InputError"]
Interface: type["bsb.storage.interfaces.Interface"]
IntersectionDataNotFoundError: type["bsb.exceptions.IntersectionDataNotFoundError"]
Intersectional: type["bsb.connectivity.detailed.shared.Intersectional"]
InvalidReferenceError: type["bsb.exceptions.InvalidReferenceError"]
InvertedRoI: type["bsb.mixins.InvertedRoI"]
JobCancelledError: type["bsb.exceptions.JobCancelledError"]
JobPool: type["bsb.services.JobPool"]
JobPoolContextError: type["bsb.exceptions.JobPoolContextError"]
JobPoolError: type["bsb.exceptions.JobPoolError"]
JobSchedulingError: type["bsb.exceptions.JobSchedulingError"]
LabelTargetting: type["bsb.simulation.targetting.LabelTargetting"]
Layer: type["bsb.topology.partition.Layer"]
LayoutError: type["bsb.exceptions.LayoutError"]
LocationTargetting: type["bsb.simulation.targetting.LocationTargetting"]
MPI: type["bsb.services.MPI"]
MPILock: type["bsb.services.MPILock"]
Meter: type["bsb.profiling.Meter"]
MissingActiveConfigError: type["bsb.exceptions.MissingActiveConfigError"]
MissingMorphologyError: type["bsb.exceptions.MissingMorphologyError"]
MissingSourceError: type["bsb.exceptions.MissingSourceError"]
MorphIOParser: type["bsb.morphologies.parsers.parser.MorphIOParser"]
Morphology: type["bsb.morphologies.Morphology"]
MorphologyDataError: type["bsb.exceptions.MorphologyDataError"]
MorphologyDependencyNode: type["bsb.storage._files.MorphologyDependencyNode"]
MorphologyDistributor: type["bsb.placement.distributor.MorphologyDistributor"]
MorphologyError: type["bsb.exceptions.MorphologyError"]
MorphologyGenerator: type["bsb.placement.distributor.MorphologyGenerator"]
MorphologyOperation: type["bsb.storage._files.MorphologyOperation"]
MorphologyParser: type["bsb.morphologies.parsers.parser.MorphologyParser"]
MorphologyRepository: type["bsb.storage.interfaces.MorphologyRepository"]
MorphologyRepositoryError: type["bsb.exceptions.MorphologyRepositoryError"]
MorphologySelector: type["bsb.morphologies.selector.MorphologySelector"]
MorphologySet: type["bsb.morphologies.MorphologySet"]
MorphologyToShapeIntersection: type["bsb.connectivity.geometric.morphology_shape_intersection.MorphologyToShapeIntersection"]
MorphologyWarning: type["bsb.exceptions.MorphologyWarning"]
NameSelector: type["bsb.morphologies.selector.NameSelector"]
NetworkDescription: type["bsb.storage.interfaces.NetworkDescription"]
NeuroMorphoScheme: type["bsb.storage._files.NeuroMorphoScheme"]
NeuroMorphoSelector: type["bsb.morphologies.selector.NeuroMorphoSelector"]
NoReferenceAttributeSignal: type["bsb.exceptions.NoReferenceAttributeSignal"]
NodeNotFoundError: type["bsb.exceptions.NodeNotFoundError"]
NoneReferenceError: type["bsb.exceptions.NoneReferenceError"]
NoopLock: type["bsb.storage.interfaces.NoopLock"]
NotParallel: type["bsb.mixins.NotParallel"]
NotSupported: type["bsb.storage.NotSupported"]
NrrdDependencyNode: type["bsb.storage._files.NrrdDependencyNode"]
NrrdVoxels: type["bsb.topology.partition.NrrdVoxels"]
Operation: type["bsb.storage._files.Operation"]
OptionDescriptor: type["bsb.option.OptionDescriptor"]
OptionError: type["bsb.exceptions.OptionError"]
PackageRequirement: type["bsb.config.types.PackageRequirement"]
PackageRequirementWarning: type["bsb.exceptions.PackageRequirementWarning"]
PackingError: type["bsb.exceptions.PackingError"]
PackingWarning: type["bsb.exceptions.PackingWarning"]
ParallelArrayPlacement: type["bsb.placement.arrays.ParallelArrayPlacement"]
Parallelepiped: type["bsb.connectivity.geometric.geometric_shapes.Parallelepiped"]
Parameter: type["bsb.simulation.parameter.Parameter"]
ParameterError: type["bsb.exceptions.ParameterError"]
ParameterValue: type["bsb.simulation.parameter.ParameterValue"]
ParserError: type["bsb.exceptions.ParserError"]
ParsesReferences: type["bsb.config.parsers.ParsesReferences"]
Partition: type["bsb.topology.partition.Partition"]
PlacementError: type["bsb.exceptions.PlacementError"]
PlacementIndications: type["bsb.cell_types.PlacementIndications"]
PlacementIndicator: type["bsb.placement.indicator.PlacementIndicator"]
PlacementRelationError: type["bsb.exceptions.PlacementRelationError"]
PlacementSet: type["bsb.storage.interfaces.PlacementSet"]
PlacementStrategy: type["bsb.placement.strategy.PlacementStrategy"]
PlacementWarning: type["bsb.exceptions.PlacementWarning"]
Plotting: type["bsb.cell_types.Plotting"]
PluginError: type["bsb.exceptions.PluginError"]
ProfilingSession: type["bsb.profiling.ProfilingSession"]
ProgressEvent: type["bsb.simulation.simulation.ProgressEvent"]
ProjectOptionDescriptor: type["bsb.option.ProjectOptionDescriptor"]
RandomMorphologies: type["bsb.placement.distributor.RandomMorphologies"]
RandomPlacement: type["bsb.placement.random.RandomPlacement"]
RandomRotations: type["bsb.placement.distributor.RandomRotations"]
ReadOnlyManager: type["bsb.storage.interfaces.ReadOnlyManager"]
ReadOnlyOptionError: type["bsb.exceptions.ReadOnlyOptionError"]
RedoError: type["bsb.exceptions.RedoError"]
Reference: type["bsb.config.refs.Reference"]
Region: type["bsb.topology.region.Region"]
RegionGroup: type["bsb.topology.region.RegionGroup"]
ReificationError: type["bsb.exceptions.ReificationError"]
Relay: type["bsb.postprocessing.Relay"]
ReportListener: type["bsb.core.ReportListener"]
RepresentativesTargetting: type["bsb.simulation.targetting.RepresentativesTargetting"]
RequirementError: type["bsb.exceptions.RequirementError"]
Rhomboid: type["bsb.topology.partition.Rhomboid"]
RootCommand: type["bsb.cli.commands.RootCommand"]
RotationDistributor: type["bsb.placement.distributor.RotationDistributor"]
RotationSet: type["bsb.morphologies.RotationSet"]
RoundRobinMorphologies: type["bsb.placement.distributor.RoundRobinMorphologies"]
Scaffold: type["bsb.core.Scaffold"]
ScaffoldError: type["bsb.exceptions.ScaffoldError"]
ScaffoldWarning: type["bsb.exceptions.ScaffoldWarning"]
ScriptOptionDescriptor: type["bsb.option.ScriptOptionDescriptor"]
SelectorError: type["bsb.exceptions.SelectorError"]
ShapeHemitype: type["bsb.connectivity.geometric.shape_shape_intersection.ShapeHemitype"]
ShapeToMorphologyIntersection: type["bsb.connectivity.geometric.shape_morphology_intersection.ShapeToMorphologyIntersection"]
ShapeToShapeIntersection: type["bsb.connectivity.geometric.shape_shape_intersection.ShapeToShapeIntersection"]
ShapesComposition: type["bsb.connectivity.geometric.geometric_shapes.ShapesComposition"]
Simulation: type["bsb.simulation.simulation.Simulation"]
SimulationBackendPlugin: type["bsb.simulation.SimulationBackendPlugin"]
SimulationComponent: type["bsb.simulation.component.SimulationComponent"]
SimulationData: type["bsb.simulation.adapter.SimulationData"]
SimulationError: type["bsb.exceptions.SimulationError"]
SimulationRecorder: type["bsb.simulation.results.SimulationRecorder"]
SimulationResult: type["bsb.simulation.results.SimulationResult"]
SimulatorAdapter: type["bsb.simulation.adapter.SimulatorAdapter"]
SomaTargetting: type["bsb.simulation.targetting.SomaTargetting"]
SourceQualityError: type["bsb.exceptions.SourceQualityError"]
Sphere: type["bsb.connectivity.geometric.geometric_shapes.Sphere"]
SphericalTargetting: type["bsb.simulation.targetting.SphericalTargetting"]
SpoofDetails: type["bsb.postprocessing.SpoofDetails"]
Stack: type["bsb.topology.region.Stack"]
Storage: type["bsb.storage.Storage"]
StorageError: type["bsb.exceptions.StorageError"]
StorageNode: type["bsb.storage.interfaces.StorageNode"]
StoredFile: type["bsb.storage.interfaces.StoredFile"]
StoredMorphology: type["bsb.storage.interfaces.StoredMorphology"]
SubTree: type["bsb.morphologies.SubTree"]
Targetting: type["bsb.simulation.targetting.Targetting"]
TopologyError: type["bsb.exceptions.TopologyError"]
TreeError: type["bsb.exceptions.TreeError"]
TypeHandler: type["bsb.config.types.TypeHandler"]
TypeHandlingError: type["bsb.exceptions.TypeHandlingError"]
UnfitClassCastError: type["bsb.exceptions.UnfitClassCastError"]
UnknownConfigAttrError: type["bsb.exceptions.UnknownConfigAttrError"]
UnknownGIDError: type["bsb.exceptions.UnknownGIDError"]
UnknownStorageEngineError: type["bsb.exceptions.UnknownStorageEngineError"]
UnmanagedPartitionError: type["bsb.exceptions.UnmanagedPartitionError"]
UnresolvedClassCastError: type["bsb.exceptions.UnresolvedClassCastError"]
UriScheme: type["bsb.storage._files.UriScheme"]
UrlScheme: type["bsb.storage._files.UrlScheme"]
VolumetricRotations: type["bsb.placement.distributor.VolumetricRotations"]
VoxelData: type["bsb.voxels.VoxelData"]
VoxelIntersection: type["bsb.connectivity.detailed.voxel_intersection.VoxelIntersection"]
VoxelSet: type["bsb.voxels.VoxelSet"]
VoxelSetError: type["bsb.exceptions.VoxelSetError"]
Voxels: type["bsb.topology.partition.Voxels"]
WeakInverter: type["bsb.config.types.WeakInverter"]
WorkflowError: type["bsb.services.WorkflowError"]
activate_session: "bsb.profiling.activate_session"
box_layout: "bsb.topology.box_layout"
branch_iter: "bsb.morphologies.branch_iter"
chunklist: "bsb.storage._chunks.chunklist"
compose_nodes: "bsb.config.compose_nodes"
copy_configuration_template: "bsb.config.copy_configuration_template"
create_engine: "bsb.storage.create_engine"
create_topology: "bsb.topology.create_topology"
discover: "bsb.plugins.discover"
discover_engines: "bsb.storage.discover_engines"
format_configuration_content: "bsb.config.format_configuration_content"
from_storage: "bsb.core.from_storage"
get_active_session: "bsb.profiling.get_active_session"
get_config_attributes: "bsb.config.get_config_attributes"
get_config_path: "bsb.config.get_config_path"
get_configuration_parser: "bsb.config.parsers.get_configuration_parser"
get_configuration_parser_classes: "bsb.config.parsers.get_configuration_parser_classes"
get_engine_node: "bsb.storage.get_engine_node"
get_engines: "bsb.storage.get_engines"
get_module_option: "bsb.options.get_module_option"
get_option: "bsb.options.get_option"
get_option_classes: "bsb.options.get_option_classes"
get_option_descriptor: "bsb.options.get_option_descriptor"
get_option_descriptors: "bsb.options.get_option_descriptors"
get_partitions: "bsb.topology.get_partitions"
get_project_option: "bsb.options.get_project_option"
get_root_regions: "bsb.topology.get_root_regions"
get_simulation_adapter: "bsb.simulation.get_simulation_adapter"
handle_cli: "bsb.cli.handle_cli"
handle_command: "bsb.cli.handle_command"
inside_mbox: "bsb.connectivity.geometric.geometric_shapes.inside_mbox"
is_module_option_set: "bsb.options.is_module_option_set"
is_partition: "bsb.topology.is_partition"
is_region: "bsb.topology.is_region"
load_root_command: "bsb.cli.commands.load_root_command"
make_config_diagram: "bsb.config.make_config_diagram"
meter: "bsb.profiling.meter"
node_meter: "bsb.profiling.node_meter"
on_main: "bsb.storage.decorators.on_main"
on_main_until: "bsb.storage.decorators.on_main_until"
open_storage: "bsb.storage.open_storage"
parse_configuration_content: "bsb.config.parse_configuration_content"
parse_configuration_content_to_dict: "bsb.config.parse_configuration_content_to_dict"
parse_configuration_file: "bsb.config.parse_configuration_file"
parse_morphology_content: "bsb.morphologies.parsers.parse_morphology_content"
parse_morphology_file: "bsb.morphologies.parsers.parse_morphology_file"
pool_cache: "bsb.services.pool_cache"
read_option: "bsb.options.read_option"
refs: "bsb.config.refs"
register_option: "bsb.options.register_option"
register_service: "bsb.services.register_service"
report: "bsb.reporting.report"
reset_module_option: "bsb.options.reset_module_option"
set_module_option: "bsb.options.set_module_option"
store_option: "bsb.options.store_option"
types: "bsb.config.types"
unregister_option: "bsb.options.unregister_option"
view_profile: "bsb.profiling.view_profile"
view_support: "bsb.storage.view_support"
walk_node_attributes: "bsb.config.walk_node_attributes"
walk_nodes: "bsb.config.walk_nodes"
warn: "bsb.reporting.warn"
