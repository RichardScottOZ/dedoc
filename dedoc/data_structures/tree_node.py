from typing import List, Optional

from dedoc.api.schema.tree_node import TreeNode as ApiTreeNode
from dedoc.data_structures.annotation import Annotation
from dedoc.data_structures.hierarchy_level import HierarchyLevel
from dedoc.data_structures.line_metadata import LineMetadata
from dedoc.data_structures.line_with_meta import LineWithMeta
from dedoc.data_structures.serializable import Serializable


class TreeNode(Serializable):
    """
    TreeNode helps to represent document as recursive tree structure.
    It has parent node (None for root ot the tree) and list of children nodes (empty list for list node).

    :ivar node_id: unique node identifier
    :ivar text: text of the node (may contain several lines)
    :ivar annotations: some metadata related to the part of the text (as font size)
    :ivar metadata: metadata refers to entire node (as node type)
    :ivar subparagraphs: list of child of this node
    :ivar parent: parent node (None for root, not none for other nodes)

    :vartype node_id: str
    :vartype text: str
    :vartype annotations: List[Annotation]
    :vartype metadata: LineMetadata
    :vartype subparagraphs: List[TreeNode]
    :vartype parent: TreeNode
    """
    def __init__(self,
                 node_id: str,
                 text: str,
                 annotations: List[Annotation],
                 metadata: LineMetadata,
                 subparagraphs: List["TreeNode"],
                 parent: Optional["TreeNode"]) -> None:
        """
        :param node_id: node id is unique in one document
        :param text: text of the node
        :param annotations: metadata related to the part of the text
        :param metadata: metadata refers to entire node
        :param subparagraphs: list of child of this node
        :param parent: parent node
        """
        self.node_id: str = node_id
        self.text: str = text
        self.annotations: List[Annotation] = annotations
        self.metadata: LineMetadata = metadata
        self.subparagraphs: List["TreeNode"] = subparagraphs
        self.parent: "TreeNode" = parent

    def to_api_schema(self) -> ApiTreeNode:
        annotations = [annotation.to_api_schema() for annotation in self.annotations]
        metadata = self.metadata.to_api_schema()
        subparagraphs = [node.to_api_schema() for node in self.subparagraphs]
        return ApiTreeNode(node_id=self.node_id, text=self.text, annotations=annotations, metadata=metadata, subparagraphs=subparagraphs)

    @staticmethod
    def create(lines: List[LineWithMeta] = None) -> "TreeNode":
        """
        Creates a root node with given text.

        :param lines: this lines should be the title of the document (or should be empty for documents without title)
        :return: root of the document tree
        """
        page_id = 0 if len(lines) == 0 else min((line.metadata.page_id for line in lines))
        line_id = 0 if len(lines) == 0 else min((line.metadata.line_id for line in lines))
        metadata = LineMetadata(page_id=page_id, line_id=line_id, hierarchy_level=HierarchyLevel.create_root())

        texts = (line.line for line in lines)
        annotations = []
        text_length = 0
        for line in lines:
            annotations.extend(TreeNode.__shift_annotations(line=line, text_length=text_length))
            TreeNode.__add_additional_page_id(start=text_length, metadata=metadata, other_line=line)

            text_length += len(line.line)
        text = "".join(texts)
        return TreeNode("0", text, annotations=annotations, metadata=metadata, subparagraphs=[], parent=None)

    def add_child(self, line: LineWithMeta) -> "TreeNode":
        """
        Create a new tree node - children of the given node from given line. Return newly created node.

        :param line: Line with meta, new node will be built from this line
        :return: return created node (child of the self)
        """
        new_node = TreeNode(
            node_id=f"{self.node_id}.{len(self.subparagraphs)}",
            text=line.line,
            annotations=line.annotations,
            metadata=line.metadata,
            subparagraphs=[],
            parent=self
        )
        self.subparagraphs.append(new_node)
        return new_node

    def add_text(self, line: LineWithMeta) -> None:
        """
        Add the text and annotations from given line, text is separated with aa len line symbol.

        :param line: line with text to add
        """
        text_length = len(self.text)
        new_annotations = self.__shift_annotations(line, text_length)

        self.__add_additional_page_id(start=len(self.text), metadata=self.metadata, other_line=line)
        self.text += line.line
        self.annotations.extend(new_annotations)

    @staticmethod
    def __shift_annotations(line: LineWithMeta, text_length: int) -> List[Annotation]:
        new_annotations = []
        for annotation in line.annotations:
            new_annotation = Annotation(start=annotation.start + text_length, end=annotation.end + text_length, name=annotation.name, value=annotation.value)
            new_annotations.append(new_annotation)
        return new_annotations

    def get_root(self) -> "TreeNode":
        """
        :return: root of the tree
        """
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def merge_annotations(self) -> None:
        from dedoc.utils.annotation_merger import AnnotationMerger

        root = self.get_root()
        stack = [root]
        merger = AnnotationMerger()
        while len(stack) > 0:
            node = stack.pop()
            node.annotations = merger.merge_annotations(node.annotations, node.text)
            for sub_node in node.subparagraphs:
                stack.append(sub_node)

    @staticmethod
    def __add_additional_page_id(start: int, metadata: LineMetadata, other_line: LineWithMeta) -> None:
        """
        Adds additional page_id metadata for multi-page nodes.

        If node is located on several pages, its metadata will contain "additional_page_id" attribute with list of dicts:
            {
                start: start index of the text on the next page,
                end: end index (not included),
                page_id: page id, where this textual part (node_text[start:end]) is located
            }
        """
        if metadata.page_id == other_line.metadata.page_id:
            return

        if hasattr(metadata, "additional_page_ids"):
            last_page_id = metadata.additional_page_ids[-1]["page_id"]
            if last_page_id == other_line.metadata.page_id:
                metadata.additional_page_ids[-1]["end"] = start + len(other_line.line)
                return

        additional_page_id = {"start": start, "end": start + len(other_line.line), "page_id": other_line.metadata.page_id}
        if hasattr(metadata, "additional_page_ids"):
            metadata.additional_page_ids.append(additional_page_id)
        else:
            metadata.additional_page_ids = [additional_page_id]
