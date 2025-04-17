from bsb import FileDependencyNode, config

from .parser import YAMLConfigurationParser


@config.node
class YamlDependencyNode(FileDependencyNode):
    """
    Configuration dependency node to load yaml files.
    """

    def load_object(self):
        content, encoding = self.file.get_content(check_store=hasattr(self, "scaffold"))
        return YAMLConfigurationParser().parse(content)[0]
