# Copyright (C) 2026 Hyee Haw
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://gnu.org>.

import ctypes
import os
import platform

import bpy
import bpy.utils.previews
import mathutils

# Constants
REFRESH_INTERVAL = 0.10  # Panel Refresh interval in seconds
NDIGITS = 1  # Number of decimal digits for float values

# Global variables
addon_keymaps = []
classes = ()

# For panel refresh
is_refreshed = False

# For icons
dir_addon = os.path.dirname(__file__)
dir_icons = os.path.join(dir_addon, "icons")
list_icon_files = []
custom_icons = None


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Defines


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Similar to bpy.context.preferences.view.ui_scale, but this value is
# using the actual DPI used for scaling in the UI.
# Maybe, system.dpi = INT(72 * bpy.context.preferences.view.ui_scale)
def ui_scale() -> float:
    """Returns the UI scale factor based on the system DPI."""
    return bpy.context.preferences.system.dpi / 72.0


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Defines to get the Dimensions of a node in the Node Editor space,
# considering the UI scale.
# Width, Height, Leftmost-X, Rightmost-X, Top-Y, Bottom-Y


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
def get_node_width(node: bpy.types.Node | None) -> float:
    """Returns the width of a node."""
    if node is None:
        return 0.0

    if node.bl_idname == "NodeReroute":
        return 0.0

    return (node.dimensions / ui_scale()).x


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
def get_node_height(node: bpy.types.Node | None) -> float:
    """Returns the height of a node."""
    if node is None:
        return 0.0

    if node.bl_idname == "NodeReroute":
        return 0.0

    return (node.dimensions / ui_scale()).y


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
def get_node_leftmost_x(node: bpy.types.Node | None) -> float:
    """Returns the leftmost X coordinate of a node."""
    if node is None:
        return 0.0

    leftmost_x = node.location_absolute.x

    return leftmost_x


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
def get_node_rightmost_x(node: bpy.types.Node | None) -> float:
    """Returns the rightmost X coordinate of a node."""
    if node is None:
        return 0.0

    leftmost_x = node.location_absolute.x
    node_width = get_node_width(node)

    return leftmost_x + node_width


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
def get_node_top_y(node: bpy.types.Node | None) -> float:
    """Returns the top Y coordinate of a node."""
    if node is None:
        return 0.0

    top_y = node.location_absolute.y

    return top_y


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
def get_node_bottom_y(node: bpy.types.Node | None) -> float:
    """Returns the bottom Y coordinate of a node."""
    if node is None:
        return 0.0

    top_y = node.location_absolute.y
    node_height = get_node_height(node)

    return top_y - node_height


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Returns the location of a socket in the node editor space.
# This method referred to the add-on by W_Cloud "Node Align"
# https://extensions.blender.org/add-ons/node-align/
def get_socket_location(socket: bpy.types.NodeSocket) -> mathutils.Vector:
    """Returns the location of a socket in the node editor space."""

    try:
        # DNA_node_types.h - bNodeSocket - runtime
        runtime_offset = 520

        if bpy.app.version >= (5, 1, 0):
            runtime_offset = 456

        # BKE_node_runtime.hh - bNodeSocketRuntime - location
        location_offset = 16

        if bpy.app.version >= (5, 2, 0):
            location_offset = 32 - 8

        if platform.system() == "Windows":  # Offset on Windows
            location_offset += 8

        runtime_address = socket.as_pointer() + runtime_offset
        runtime_address = ctypes.c_void_p.from_address(runtime_address).value

        if runtime_address is None:
            raise Exception("Failed to get runtime address.")

        location_address = runtime_address + location_offset
        sequence = (ctypes.c_float * 2).from_address(location_address)
        location = mathutils.Vector((sequence[0], sequence[1]))

        return location / ui_scale()

    except Exception as e:
        raise Exception("Get socket location error: " + str(e))


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Defines to checks if a node is not to be touched
def is_node_not_to_touch(
    node: bpy.types.Node, active_node: bpy.types.Node
) -> bool:
    """Checks if a node must not be touched."""

    def is_descendant_of(
        descendant: bpy.types.Node, ancestor: bpy.types.Node
    ) -> bool:
        """
        Recursively checks if the node is a descendant of the ancestor.
        """
        if descendant == ancestor:
            return True
        elif descendant.parent is not None:
            return is_descendant_of(descendant.parent, ancestor)
        else:
            return False

    return (
        node == active_node
        or is_descendant_of(node, active_node)
        or node.bl_idname == "NodeFrame"
    )


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Addon Preference


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Preferences for Right-Angled Node Connection
class RightAngledPreferences(bpy.types.AddonPreferences):
    """Preferences for Right-Angled Node Connection."""

    if __package__ is None:
        bl_idname = "__main__"
    else:
        bl_idname = __package__

    space: bpy.props.FloatProperty(
        name="Space Length",
        description="Space length between nodes",
        default=22.7,
        min=10.0,
        max=240.0,
    )
    width: bpy.props.FloatProperty(
        name="Node Width",
        description="Width of each node",
        default=140.0,
        min=70.0,
        max=420.0,
    )
    enable_sidebar: bpy.props.BoolProperty(
        name="Enable Sidebar",
        description="Enable the sidebar for Right-Angled Node Connection.",
        default=True,
    )

    def draw(self, context):
        layout = self.layout

        layout.label(text="Size Settings:")
        row = layout.row()
        row.alignment = "LEFT"
        row.prop(self, "width")
        row.prop(self, "space")

        layout.label(text="Quick Access Settings:")

        window_manager = context.window_manager
        keyconfig = window_manager.keyconfigs.addon
        if keyconfig is None:
            return

        keymap = keyconfig.keymaps.get("Node Editor")
        if keymap is None:
            return

        popup_idname = NODE_MT_rightangled_main_popup.bl_idname
        for keymap_item in keymap.keymap_items:
            if keymap_item.idname != "wm.call_menu":
                continue
            if keymap_item.properties.name != popup_idname:
                continue

            row = layout.row()
            row.alignment = "LEFT"
            row.context_pointer_set("Keymap", keymap)
            row.prop(keymap_item, "active", text="Enable")
            row.prop(keymap_item, "map_type", text="")
            row.prop(keymap_item, "type", text="", full_event=True)

        layout.label(text="Sidebar Settings:")
        row = layout.row()
        row.alignment = "LEFT"
        row.prop(self, "enable_sidebar", text="Enable")


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Operators


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Base Operator for Right-Angled Node Connection
class BaseOperator(bpy.types.Operator):
    """Base Operator for Right-Angled Node Connection."""

    bl_idname = "node.rightangled_base_operator"
    bl_label = "Right-Angled Node Connection"
    bl_options = {"REGISTER", "UNDO"}  # noqa: RUF012

    @classmethod
    def poll(cls, context) -> bool:
        """Poll method to check if the operator can be executed."""
        active_node = getattr(context, "active_node", None)
        if active_node is None:
            return False

        return not (
            active_node.select is False
            or len(getattr(context, "selected_nodes", [])) < 2
        )

    def get_preferences(self, context) -> RightAngledPreferences:
        """Returns the preferences for this Addon."""
        return bpy.context.preferences.addons[__package__].preferences


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Recursively adjust the position of connected nodes to create
# right-angled connections
class NODE_OT_rightangled_right_angle_connection(BaseOperator):
    """
    Recursively adjust the position of connected nodes to create
    right-angled connections.
    """

    bl_idname = "node.rightangled_right_angle_connection"
    bl_label = "Right-Angle Connection"

    def execute(self, context):

        active_node = getattr(context, "active_node", None)
        selected_nodes = getattr(context, "selected_nodes", [])

        list_selected_nodes = list(selected_nodes).copy()

        if active_node is None or active_node not in selected_nodes:
            return {"CANCELLED"}

        self.rightangle_connection(context, active_node)

        # rightangle_connection may deselect nodes, so we reselect them
        for node in list_selected_nodes:
            node.select = True

        return {"FINISHED"}

    @staticmethod
    def set_node_position_socket_origin(
        this_node: bpy.types.Node,
        this_socket: bpy.types.NodeSocket,
        that_node: bpy.types.Node,
        that_socket: bpy.types.NodeSocket,
        offset_y: float = 0.0,
    ) -> float:
        """
        Adjusts the position of a node based on the socket locations.
        """
        if this_node.bl_idname == "NodeReroute":
            this_location = this_node.location_absolute
        else:
            this_location = get_socket_location(this_socket)

        if that_node.bl_idname == "NodeReroute":
            that_location = that_node.location_absolute
        else:
            that_location = get_socket_location(that_socket)
            that_location += mathutils.Vector((0.0, offset_y))
            # get_socket_location() value is not refreshed before
            # display update.

        location_diff = that_location - this_location

        if (  # If both nodes are Reroute nodes, adjustable vertically
            abs(location_diff.x) < abs(location_diff.y)
            and this_node.bl_idname == "NodeReroute"
            and that_node.bl_idname == "NodeReroute"
        ):
            this_node.location_absolute.x += location_diff.x

            return 0.0

        else:  # adjust horizontally
            this_node.location_absolute.y += location_diff.y

            return location_diff.y

    def rightangle_connection(
        self,
        context: bpy.types.Context,
        this_node: bpy.types.Node,
        from_link: bpy.types.NodeLink | None = None,
        offset_y: float = 0.0,
    ) -> None:
        """
        Recursively adjust the position of connected nodes to create
        right-angled connections.
        """
        list_sockets = list(this_node.inputs) + list(this_node.outputs)
        for this_socket in list_sockets:
            if not this_socket.is_linked:
                continue

            if this_socket.links is None:
                continue

            for link in this_socket.links:
                if link == from_link:
                    continue

                if link.to_socket != this_socket:
                    that_socket = link.to_socket
                    that_node = link.to_node
                else:
                    that_socket = link.from_socket
                    that_node = link.from_node

                if that_node is None or that_socket is None:
                    continue

                if that_node.select is False:
                    continue

                # If this socket is a multi-input socket, skip adjusting
                # the position of that node
                next_offset_y = 0.0
                if not this_socket.is_multi_input:
                    next_offset_y = self.set_node_position_socket_origin(
                        that_node,
                        that_socket,
                        this_node,
                        this_socket,
                        offset_y=offset_y,
                    )
                # Deselect the node to avoid infinite recursion
                this_node.select = False

                self.rightangle_connection(
                    context,
                    that_node,
                    from_link=link,
                    offset_y=next_offset_y,
                )


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Sets the width of the selected nodes.
class NODE_OT_rightangled_set_node_width(BaseOperator):
    """Sets the width of the selected nodes."""

    bl_idname = "node.rightangled_set_node_width"
    bl_label = "Set Node Width"

    @classmethod
    def poll(cls, context):
        """Poll method to check if the operator can be executed."""
        return len(getattr(context, "selected_nodes", [])) > 0

    def execute(self, context):
        """Set the width of the selected nodes."""
        node_width = self.get_preferences(context).width

        if context.selected_nodes is None:
            return {"FINISHED"}

        for node in context.selected_nodes:
            nodetype = node.bl_idname
            if nodetype == "NodeReroute" or nodetype == "NodeFrame":
                continue

            node.width = node_width

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Align Selected Nodes to the Left
class NODE_OT_rightangled_align_left(BaseOperator):
    """Aligns selected nodes to the left of the active node."""

    bl_idname = "node.rightangled_align_left"
    bl_label = "Align Left"

    def execute(self, context):

        if context.active_node is None or context.selected_nodes is None:
            return {"CANCELLED"}

        active_node = context.active_node

        target_x = get_node_leftmost_x(active_node)
        for node in context.selected_nodes:
            if is_node_not_to_touch(node, active_node):
                continue

            node.location_absolute.x = target_x

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Align Selected Nodes to the Horizontal Center of the Active Node
class NODE_OT_rightangled_align_center(BaseOperator):
    """Aligns selected nodes to the horizontal center of
    the active node."""

    bl_idname = "node.rightangled_align_center"
    bl_label = "Align Center"

    def execute(self, context):
        if context.active_node is None or context.selected_nodes is None:
            return {"CANCELLED"}

        active_node = context.active_node

        node_width = get_node_width(active_node)
        target_x = get_node_leftmost_x(active_node) + (node_width / 2)
        for node in context.selected_nodes:
            if is_node_not_to_touch(node, active_node):
                continue

            nodetype = node.bl_idname
            if is_node_not_to_touch(node, active_node):
                continue

            node_width = get_node_width(node)
            node.location_absolute.x = target_x - (node_width / 2)

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Align Selected Nodes to the Right of the Active Node
class NODE_OT_rightangled_align_right(BaseOperator):
    """Aligns selected nodes to the right of the active node."""

    bl_idname = "node.rightangled_align_right"
    bl_label = "Align Right"

    def execute(self, context):
        if context.active_node is None or context.selected_nodes is None:
            return {"CANCELLED"}

        active_node = context.active_node

        node_width = get_node_width(active_node)
        target_x = get_node_rightmost_x(active_node)
        for node in context.selected_nodes:
            if is_node_not_to_touch(node, active_node):
                continue

            nodetype = node.bl_idname
            if is_node_not_to_touch(node, active_node):
                continue

            node_width = get_node_width(node)
            node.location_absolute.x = target_x - node_width

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Align Selected Nodes to the Top of the Active Node
class NODE_OT_rightangled_align_top(BaseOperator):
    """Aligns selected nodes to the top of the active node."""

    bl_idname = "node.rightangled_align_top"
    bl_label = "Align Top"

    def execute(self, context):
        if context.active_node is None or context.selected_nodes is None:
            return {"CANCELLED"}

        active_node = context.active_node

        target_y = get_node_top_y(active_node)
        for node in context.selected_nodes:
            if is_node_not_to_touch(node, active_node):
                continue

            node.location_absolute.y = target_y

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Align Selected Nodes to the Bottom of the Active Node
class NODE_OT_rightangled_align_bottom(BaseOperator):
    """Aligns selected nodes to the bottom of the active node."""

    bl_idname = "node.rightangled_align_bottom"
    bl_label = "Align Bottom"

    def execute(self, context):
        if context.active_node is None or context.selected_nodes is None:
            return {"CANCELLED"}

        active_node = context.active_node

        node_height = get_node_height(active_node)
        target_y = get_node_bottom_y(active_node)
        for node in context.selected_nodes:
            if is_node_not_to_touch(node, active_node):
                continue

            node_height = get_node_height(node)
            node.location_absolute.y = target_y + node_height

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Adjust the Spaces between Selected Nodes Horizontally
class NODE_OT_rightangled_space_horizontal(BaseOperator):
    """Adjust the Spaces between selected nodes horizontally."""

    bl_idname = "node.rightangled_space_horizontal"
    bl_label = "Spaces Horizontally"

    def execute(self, context):
        if context.active_node is None or context.selected_nodes is None:
            return {"CANCELLED"}

        active_node = context.active_node
        space = self.get_preferences(context).space

        # Sort selected nodes based on their X location
        nodes_left = {}
        nodes_right = {}
        list_nodes_same = []
        for node in context.selected_nodes:
            if is_node_not_to_touch(node, active_node):
                continue

            x_location = round(node.location_absolute.x, NDIGITS)

            if node.location_absolute.x < active_node.location_absolute.x:
                list_nodes = nodes_left.get(x_location)

                if list_nodes is None:
                    nodes_left[x_location] = [node]
                else:
                    list_nodes.append(node)
            elif node.location_absolute.x > active_node.location_absolute.x:
                list_nodes = nodes_right.get(x_location)

                if list_nodes is None:
                    nodes_right[x_location] = [node]
                else:
                    list_nodes.append(node)
            else:
                list_nodes_same.append(node)

        # Calculate the Node's new X location with the specified
        # Space length (horizontally)
        base_x = get_node_leftmost_x(active_node)
        for node in list_nodes_same:
            node.location_absolute.x = base_x

        base_x = get_node_leftmost_x(active_node)
        for before_x in sorted(nodes_left.keys(), reverse=True):
            leftmost_x = base_x

            for node in nodes_left[before_x]:
                node_width = get_node_width(node)
                after_x = base_x - space - node_width
                node.location_absolute.x = after_x

                if after_x < leftmost_x:
                    leftmost_x = after_x

            base_x = leftmost_x  # Update base_x

        base_x = get_node_rightmost_x(active_node)
        for before_x in sorted(nodes_right.keys()):
            rightmost_x = base_x

            for node in nodes_right[before_x]:
                node_width = get_node_width(node)
                after_x = base_x + space
                node.location_absolute.x = after_x

                if after_x + node_width > rightmost_x:
                    rightmost_x = after_x + node_width

            base_x = rightmost_x  # Update base_x

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Adjust the Spaces between Selected Nodes Vertically
class NODE_OT_rightangled_space_vertical(BaseOperator):
    """Adjust the Spaces between Selected Nodes Vertically."""

    bl_idname = "node.rightangled_space_vertical"
    bl_label = "Spaces Vertically"

    def execute(self, context):
        if context.active_node is None or context.selected_nodes is None:
            return {"CANCELLED"}

        active_node = context.active_node
        space = self.get_preferences(context).space

        # Sort selected nodes based on their Y location
        nodes_top = {}
        nodes_bottom = {}
        list_nodes_same = []
        for node in context.selected_nodes:
            if is_node_not_to_touch(node, active_node):
                continue

            y_location = round(node.location_absolute.y, NDIGITS)

            if node.location_absolute.y < active_node.location_absolute.y:
                list_nodes = nodes_bottom.get(y_location)

                if list_nodes is None:
                    nodes_bottom[y_location] = [node]
                else:
                    list_nodes.append(node)

            elif node.location_absolute.y > active_node.location_absolute.y:
                list_nodes = nodes_top.get(y_location)

                if list_nodes is None:
                    nodes_top[y_location] = [node]
                else:
                    list_nodes.append(node)

            else:
                list_nodes_same.append(node)

        # Calculate the Node's new Y location with the specified
        # Space length (vertically)
        base_y = get_node_top_y(active_node)
        for node in list_nodes_same:
            node.location_absolute.y = base_y

        base_y = get_node_bottom_y(active_node)
        for before_y in sorted(nodes_bottom.keys(), reverse=True):
            bottom_y = base_y

            for node in nodes_bottom[before_y]:
                node_height = get_node_height(node)
                after_y = base_y - space
                node.location_absolute.y = after_y

                if after_y - node_height < bottom_y:
                    bottom_y = after_y - node_height

            base_y = bottom_y  # Update base_y

        base_y = get_node_top_y(active_node)
        for before_y in sorted(nodes_top.keys()):
            top_y = base_y + space

            for node in nodes_top[before_y]:
                node_height = get_node_height(node)
                after_y = base_y + space + node_height
                node.location_absolute.y = after_y

                if after_y > top_y:
                    top_y = after_y

            base_y = top_y  # Update base_y

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Displays information about the active node in a popup dialog
class NODE_OT_rightangled_show_active_info(BaseOperator):
    """Displays information about the active node."""

    bl_idname = "node.rightangled_show_active_info"
    bl_label = "Active Node Info"

    @classmethod
    def poll(cls, context):
        """Poll method to check if the operator can be executed."""
        return not (
            getattr(context, "active_node", None) is None
            or len(getattr(context, "selected_nodes", [])) < 1
        )

    def draw(self, context):
        layout = self.layout

        if layout is None:
            return

        active_node = context.active_node

        if active_node is not None:
            node_name = active_node.name

            layout.label(text=node_name, icon="NODE")
            layout.label(text="Location:")

            nodetype = active_node.bl_idname

            column = layout.column(align=True)
            if nodetype == "NodeFrame":
                column.enabled = False

            column.prop(active_node, "location_absolute", index=0, text="X")
            column.prop(active_node, "location_absolute", index=1, text="Y")

            layout.label(text="Dimension:")

            column = layout.column(align=True)
            if nodetype == "NodeReroute" or nodetype == "NodeFrame":
                column.enabled = False

            column.prop(active_node, "process_width", text="Width")
            column.prop(active_node, "process_height", text="Height")

        else:
            layout.label(text="No active node found.", icon="NODE")

    def execute(self, context):
        # Display the popup with the active node information
        return context.window_manager.invoke_popup(self)


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Refreshes the active node information timer
class NODE_OT_rightangled_refresh_timer(BaseOperator):
    """Refreshes the active node information timer."""

    bl_idname = "node.rightangled_refresh_timer"
    bl_label = "Refresh Active Node Info"

    @classmethod
    def poll(cls, context):
        """Poll method to check if the operator can be executed."""
        return True

    def execute(self, context):
        global is_refreshed

        is_refreshed = True  # Set "refreshed" flag

        props = getattr(context.window_manager, "rightangled_props", None)
        if props is None:
            return

        props.is_refreshing = True

        if bpy.app.timers.is_registered(force_redraw_node_editor_timer):
            bpy.app.timers.unregister(force_redraw_node_editor_timer)

        bpy.app.timers.register(
            force_redraw_node_editor_timer,
            first_interval=REFRESH_INTERVAL * 10,
            persistent=True,
        )

        return {"FINISHED"}


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Menu


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Align Submenu
class NODE_MT_rightangled_align_menu(bpy.types.Menu):
    """Align Submenu for Right-Angled Node Connection."""

    bl_label = "Align"
    bl_idname = "NODE_MT_rightangled_align_menu"

    def draw(self, context):
        global custom_icons
        layout = self.layout

        if custom_icons is None or layout is None:
            return

        if custom_icons.get("align_top") is not None:
            layout.operator(
                "node.rightangled_align_top",
                text="Top",
                icon_value=custom_icons["align_top"].icon_id,
            )
        layout.separator()

        if custom_icons.get("align_left") is not None:
            layout.operator(
                "node.rightangled_align_left",
                text="Left",
                icon_value=custom_icons["align_left"].icon_id,
            )
        if custom_icons.get("align_center") is not None:
            layout.operator(
                "node.rightangled_align_center",
                text="Center",
                icon_value=custom_icons["align_center"].icon_id,
            )
        if custom_icons.get("align_right") is not None:
            layout.operator(
                "node.rightangled_align_right",
                text="Right",
                icon_value=custom_icons["align_right"].icon_id,
            )
        layout.separator()

        if custom_icons.get("align_bottom") is not None:
            layout.operator(
                "node.rightangled_align_bottom",
                text="Bottom",
                icon_value=custom_icons["align_bottom"].icon_id,
            )


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Adjust the Spaces Submenu
class NODE_MT_rightangled_space_menu(bpy.types.Menu):
    """Spaces Submenu for Right-Angled Node Connection."""

    bl_label = "Spaces"
    bl_idname = "NODE_MT_rightangled_space_menu"

    def draw(self, context):
        global custom_icons
        layout = self.layout

        if custom_icons is None or layout is None:
            return

        if custom_icons.get("space_horizontal") is not None:
            layout.operator(
                "node.rightangled_space_horizontal",
                text="Horizontal",
                icon_value=custom_icons["space_horizontal"].icon_id,
            )
        if custom_icons.get("space_vertical") is not None:
            layout.operator(
                "node.rightangled_space_vertical",
                text="Vertical",
                icon_value=custom_icons["space_vertical"].icon_id,
            )


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Main Popup Menu for Right-Angled Node Connection
class NODE_MT_rightangled_main_popup(bpy.types.Menu):
    """Main Popup Menu for Right-Angled Node Connection."""

    bl_label = "Right-Angled Node Connection"
    bl_idname = "NODE_MT_rightangled_main_popup"

    def draw(self, context):
        global custom_icons
        layout = self.layout

        if custom_icons is None or layout is None:
            return

        if custom_icons.get("information") is not None:
            layout.operator(
                "node.rightangled_show_active_info",
                text="Information (Active Node)",
                icon_value=custom_icons["information"].icon_id,
            )
        layout.separator()

        if custom_icons.get("rightangled") is not None:
            layout.operator(
                "node.rightangled_right_angle_connection",
                text="Right-Angle Connection",
                icon_value=custom_icons["rightangled"].icon_id,
            )
        if custom_icons.get("node_width") is not None:
            layout.operator(
                "node.rightangled_set_node_width",
                text="Width (Set Uniform Node Width)",
                icon_value=custom_icons["node_width"].icon_id,
            )
        layout.separator()

        layout.menu("NODE_MT_rightangled_align_menu", text="Align")
        layout.menu("NODE_MT_rightangled_space_menu", text="Spacing")


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Sidebar Panel


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Sidebar Panel for Right-Angled Node Connection
class NODE_PT_rightangled_sidebar(bpy.types.Panel):
    """Sidebar Panel for Right-Angled Node Connection."""

    bl_label = "Right-Angled Node Connection"
    bl_idname = "NODE_PT_rightangled_sidebar"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Right-Angled"

    @classmethod
    def poll(cls, context):
        """Poll method to check if the panel can be displayed."""
        addon = context.preferences.addons[__package__]
        if addon is None:
            return False

        preferences = addon.preferences
        return preferences.enable_sidebar

    def draw(self, context):
        global custom_icons

        if custom_icons is None:
            return

        global is_refreshed

        is_refreshed = True  # Set "refreshed" flag

        addon = context.preferences.addons[__package__]
        if addon is None:
            return
        preferences = addon.preferences

        props = getattr(context.window_manager, "rightangled_props", None)
        if props is None:
            return

        # Start the refresh process if it is not already refreshing
        if not props.is_refreshing:
            props.is_refreshing = True

            if bpy.app.timers.is_registered(force_redraw_node_editor_timer):
                bpy.app.timers.unregister(force_redraw_node_editor_timer)

            bpy.app.timers.register(
                force_redraw_node_editor_timer,
                first_interval=REFRESH_INTERVAL * 10,
                persistent=True,
            )

        layout = self.layout
        if layout is None:
            return

        layout.label(text="Active Node Information:")

        active_node = context.active_node

        if active_node is not None:
            box = layout.box()

            node_name = active_node.name

            box.label(text=node_name, icon="NODE")
            box.label(text="Location:")
            nodetype = active_node.bl_idname

            column = box.column(align=True)
            if nodetype == "NodeFrame":
                column.enabled = False

            column.prop(active_node, "location_absolute", index=0, text="X")
            column.prop(active_node, "location_absolute", index=1, text="Y")

            box.label(text="Dimensions:")

            column = box.column(align=True)
            if nodetype == "NodeReroute" or nodetype == "NodeFrame":
                column.enabled = False

            column.prop(active_node, "process_width", text="Width")
            column.prop(active_node, "process_height", text="Height")

            box.operator(
                "node.rightangled_refresh_timer",
                text="Refresh Information",
                icon="FILE_REFRESH",
            )

            box.separator()

        else:
            box = layout.box()

            box.label(text="No active node found.", icon="NODE")

        layout.separator()

        if custom_icons.get("rightangled") is not None:
            layout.operator(
                "node.rightangled_right_angle_connection",
                text="Right-Angle Connection",
                icon_value=custom_icons["rightangled"].icon_id,
            )
        layout.separator()

        if custom_icons.get("node_width") is not None:
            layout.operator(
                "node.rightangled_set_node_width",
                text="Set Uniform Node Width",
                icon_value=custom_icons["node_width"].icon_id,
            )
        layout.prop(preferences, "width")

        layout.separator()

        layout.label(text="Align Selected Nodes:")

        if custom_icons.get("align_top") is not None:
            layout.operator(
                "node.rightangled_align_top",
                text="Top",
                icon_value=custom_icons["align_top"].icon_id,
            )
        row = layout.row()

        if custom_icons.get("align_left") is not None:
            row.operator(
                "node.rightangled_align_left",
                text="Left",
                icon_value=custom_icons["align_left"].icon_id,
            )
        if custom_icons.get("align_center") is not None:
            row.operator(
                "node.rightangled_align_center",
                text="Center",
                icon_value=custom_icons["align_center"].icon_id,
            )
        if custom_icons.get("align_right") is not None:
            row.operator(
                "node.rightangled_align_right",
                text="Right",
                icon_value=custom_icons["align_right"].icon_id,
            )

        if custom_icons.get("align_bottom") is not None:
            layout.operator(
                "node.rightangled_align_bottom",
                text="Bottom",
                icon_value=custom_icons["align_bottom"].icon_id,
            )
        layout.separator()

        layout.label(text="Set Consistent Spacing:")

        if custom_icons.get("space_horizontal") is not None:
            layout.operator(
                "node.rightangled_space_horizontal",
                text="Horizontal Space",
                icon_value=custom_icons["space_horizontal"].icon_id,
            )
        if custom_icons.get("space_vertical") is not None:
            layout.operator(
                "node.rightangled_space_vertical",
                text="Vertical Space",
                icon_value=custom_icons["space_vertical"].icon_id,
            )
        layout.prop(preferences, "space")

        window_manager = context.window_manager
        keyconfig = window_manager.keyconfigs.addon
        if keyconfig is None:
            return

        keymap = keyconfig.keymaps.get("Node Editor")
        if keymap is None:
            return

        popup_idname = NODE_MT_rightangled_main_popup.bl_idname
        for keymap_item in keymap.keymap_items:
            if keymap_item.idname != "wm.call_menu":
                continue
            if keymap_item.properties.name != popup_idname:
                continue
            if keymap_item.active is False:
                continue

            layout.separator()
            layout.label(text="Quick Access:")

            row = layout.row()
            row.context_pointer_set("Keymap", keymap)
            row.prop(keymap_item, "map_type", text="")
            row.prop(keymap_item, "type", text="", full_event=True)


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Global Variables for Addon Paths and Icon Files

dir_addon = os.path.dirname(__file__)
dir_icons = os.path.join(dir_addon, "icons")

list_icon_files = [
    "rightangled",
    "node_width",
    "align_left",
    "align_center",
    "align_right",
    "align_top",
    "align_bottom",
    "space_horizontal",
    "space_vertical",
    "information",
]


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Handlers for the process_width and process_height properties of a node


def get_node_process_width(self):
    """Get Handler for the process_width property of a node."""
    if self.bl_idname == "NodeReroute":
        return 0.0

    return self.width


def set_node_process_width(self, value):
    """Set Handler for the process_width property of a node."""
    if self.bl_idname != "NodeReroute":
        self.width = value


def get_node_process_height(self):
    """Get Handler for the process_height property of a node."""
    if self.bl_idname == "NodeReroute":
        return 0.0

    return (self.dimensions / ui_scale()).y


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Setup for Display Refreshing in the Node Editor Sidebar Panel

is_refreshed = False  # Indicate if the display has been refreshed


def force_redraw_node_editor_timer():
    """Force redraw of the Node Editor area."""
    global is_refreshed

    if not is_refreshed:
        context = bpy.context
        props = getattr(context.window_manager, "rightangled_props", None)
        if props is None:
            return None  # Stop the timer

        props.is_refreshing = False

        return None  # Stop the timer

    is_refreshed = False  # Reset the flag for the next refresh

    # Refresh all Node Editor areas to update the display
    # If Refreshed, the flag is_refreshed will be set to True
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "NODE_EDITOR":
                area.tag_redraw()

    return REFRESH_INTERVAL


class RightAngledGlobalProperties(bpy.types.PropertyGroup):
    """Property Group for Right-Angled Node Connection."""

    is_refreshing: bpy.props.BoolProperty(
        name="Is Refreshing Display",
        description="Indicates if the node information is being refreshed",
        default=False,
    )


# noqa: E501 ------2---------3---------4---------5---------6---------7-]------]8
# Register and Unregister Functions

classes = (
    RightAngledPreferences,
    RightAngledGlobalProperties,
    NODE_OT_rightangled_right_angle_connection,
    NODE_OT_rightangled_set_node_width,
    NODE_OT_rightangled_align_left,
    NODE_OT_rightangled_align_center,
    NODE_OT_rightangled_align_right,
    NODE_OT_rightangled_align_top,
    NODE_OT_rightangled_align_bottom,
    NODE_OT_rightangled_space_horizontal,
    NODE_OT_rightangled_space_vertical,
    NODE_OT_rightangled_show_active_info,
    NODE_OT_rightangled_refresh_timer,
    NODE_MT_rightangled_align_menu,
    NODE_MT_rightangled_space_menu,
    NODE_MT_rightangled_main_popup,
    NODE_PT_rightangled_sidebar,
)


def register():
    # Load custom icons
    global custom_icons
    custom_icons = bpy.utils.previews.new()

    for icon_name in list_icon_files:
        icon_path = os.path.join(dir_icons, icon_name + ".svg")
        custom_icons.load(icon_name, icon_path, "IMAGE")

    # Class registration
    for cls in classes:
        bpy.utils.register_class(cls)

    # Shortcut registration
    global addon_keymaps
    window_manager = bpy.context.window_manager
    keyconfig = window_manager.keyconfigs.addon
    if keyconfig:
        keymap = keyconfig.keymaps.new(
            name="Node Editor", space_type="NODE_EDITOR"
        )
        keymap_item = keymap.keymap_items.new(  # Shift + Ctrl + A
            idname="wm.call_menu", type="A", value="PRESS", shift=1, ctrl=1
        )
        popup_idname = NODE_MT_rightangled_main_popup.bl_idname
        keymap_item.properties.name = popup_idname
        addon_keymaps.append((keymap, keymap_item))

    # Extend the custom property to all node classes (bpy.types.Node)
    bpy.types.Node.process_width = bpy.props.FloatProperty(
        name="Node Width",
        description="Width of the node",
        precision=3,
        get=get_node_process_width,
        set=set_node_process_width,
    )
    bpy.types.Node.process_height = bpy.props.FloatProperty(
        name="Node Height",
        description="Height of the node",
        precision=3,
        get=get_node_process_height,
        options={"READ_ONLY"},
    )
    # Register the global properties for Right-Angled Node Connection
    bpy.types.WindowManager.rightangled_props = bpy.props.PointerProperty(
        type=RightAngledGlobalProperties
    )


def unregister():
    # Stop the refresh process if it is still running
    global is_refreshed
    is_refreshed = True  # Set "refreshed" flag

    window_manager = bpy.context.window_manager
    props = getattr(window_manager, "rightangled_props", None)

    if props is not None and getattr(props, "is_refreshing", None) is not None:
        props.is_refreshing = False  # Stop the refresh process

    # Unregister the timer if it is registered
    if bpy.app.timers.is_registered(force_redraw_node_editor_timer):
        bpy.app.timers.unregister(force_redraw_node_editor_timer)

    # Delete the global properties for Right-Angled Node Connection
    if hasattr(bpy.types.WindowManager, "rightangled_props"):
        del bpy.types.WindowManager.rightangled_props

    # Delete the custom node properties when unregistering
    if hasattr(bpy.types.Node, "process_width"):
        del bpy.types.Node.process_width
    if hasattr(bpy.types.Node, "process_height"):
        del bpy.types.Node.process_height

    # Delete the keymaps when unregistering
    global addon_keymaps
    for keymap, keymap_item in addon_keymaps:
        keymap.keymap_items.remove(keymap_item)

    addon_keymaps.clear()

    # Delete the classes when unregistering
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Delete the custom icons when unregistering
    global custom_icons
    if custom_icons is not None:
        bpy.utils.previews.remove(custom_icons)
        custom_icons = None
