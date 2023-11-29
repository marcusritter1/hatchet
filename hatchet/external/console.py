# -*- coding: utf-8 -*-

# Copyright (c) 2014-2018, Joe Rickerby and contributors
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from ..version import __version__

import pandas as pd
import numpy as np
import warnings
from ..util.colormaps import ColorMaps


class ConsoleRenderer:
    def __init__(self, unicode=False, color=False):
        self.unicode = unicode
        self.color = color
        self.visited = []

    def render(self, roots, dataframe, **kwargs):
        self.render_header = kwargs["render_header"]

        if self.render_header:
            result = self.render_preamble()
        else:
            result = ""

        if roots is None:
            result += "The graph is empty.\n\n"
            return result

        self.metric_columns = kwargs["metric_column"]
        self.annotation_column = kwargs["annotation_column"]
        self.precision = kwargs["precision"]
        self.name = kwargs["name_column"]
        self.expand = kwargs["expand_name"]
        self.context = kwargs["context_column"]
        self.rank = kwargs["rank"]
        self.thread = kwargs["thread"]
        self.depth = kwargs["depth"]
        self.highlight = kwargs["highlight_name"]
        self.colormap = kwargs["colormap"]
        self.invert_colormap = kwargs["invert_colormap"]
        self.colormap_annotations = kwargs["colormap_annotations"]
        self.min_value = kwargs["min_value"]
        self.max_value = kwargs["max_value"]
        try:
            self.modeler_config = kwargs["modeler_config"]
        except KeyError:
            self.modeler_config = None

        if self.color:
            self.colors = self.colors_enabled
            # set the colormap based on user input
            self.colors.colormap = ColorMaps().get_colors(
                self.colormap, self.invert_colormap
            )

            if self.annotation_column and self.colormap_annotations:
                self.colors_annotations = self.colors_enabled()
                if isinstance(self.colormap_annotations, (str, list)):
                    if isinstance(self.colormap_annotations, str):
                        self.colors_annotations.colormap = ColorMaps().get_colors(
                            self.colormap_annotations, False
                        )
                    elif isinstance(self.colormap_annotations, list):
                        self.colors_annotations.colormap = self.colormap_annotations
                    self.colors_annotations_mapping = sorted(
                        list(dataframe[self.modeler_config][self.annotation_column].apply(
                            str).unique())
                    )
                elif isinstance(self.colormap_annotations, dict):
                    self.colors_annotations_mapping = self.colormap_annotations
        else:
            self.colors = self.colors_disabled

        if isinstance(self.metric_columns, str):
            self.primary_metric = self.metric_columns
            self.second_metric = None
        elif isinstance(self.metric_columns, list):
            if len(self.metric_columns) > 2:
                warnings.warn(
                    "More than 2 metrics specified in metric_column=. Tree() will only show 2 metrics at a time. The remaining metrics will not be shown.",
                    SyntaxWarning,
                )
                self.primary_metric = self.metric_columns[0]
                self.second_metric = self.metric_columns[1]
            elif len(self.metric_columns) == 2:
                self.primary_metric = self.metric_columns[0]
                self.second_metric = self.metric_columns[1]
            elif len(self.metric_columns) == 1:
                self.primary_metric = self.metric_columns[0]
                self.second_metric = None

        if self.primary_metric not in dataframe.columns and self.primary_metric not in dataframe[self.modeler_config].columns:
            raise KeyError(
                "metric_column={} does not exist in the dataframe, please select a valid column. See a list of the available metrics with GraphFrame.show_metric_columns().".format(
                    self.primary_metric
                )
            )
        if (
            self.second_metric is not None
            and self.second_metric not in dataframe.columns
        ):
            raise KeyError(
                "metric_column={} does not exist in the dataframe, please select a valid column. See a list of the available metrics with GraphFrame.show_metric_columns().".format(
                    self.second_metric
                )
            )

        # grab the min and max value for the primary metric, ignoring inf and
        # nan values

        if "rank" in dataframe.index.names:
            metric_series = (dataframe.xs(self.rank, level=1))[
                self.primary_metric]
        else:
            if self.modeler_config is not None and self.primary_metric not in dataframe.columns:
                metric_series = dataframe[self.modeler_config][self.primary_metric]
            else:
                metric_series = dataframe[self.primary_metric]
        isfinite_mask = np.isfinite(metric_series.values)
        filtered_series = pd.Series(
            metric_series.values[isfinite_mask], metric_series.index[isfinite_mask]
        )

        self.max_metric = self.max_value if self.max_value else filtered_series.max()
        self.min_metric = self.min_value if self.min_value else filtered_series.min()

        if self.unicode:
            self.lr_arrows = {"◀": "◀ ", "▶": "▶ "}
        else:
            self.lr_arrows = {"◀": "< ", "▶": "> "}

        for root in sorted(roots, key=lambda n: n._hatchet_nid):
            result += self.render_frame(root, dataframe)

        if self.color is True:
            result += self.render_legend(dataframe)

        if self.unicode:
            return result
        else:
            return result.encode("utf-8")

    # pylint: disable=W1401
    def render_preamble(self):
        lines = [
            r"    __          __       __         __ ",
            r"   / /_  ____ _/ /______/ /_  ___  / /_",
            r"  / __ \/ __ `/ __/ ___/ __ \/ _ \/ __/",
            r" / / / / /_/ / /_/ /__/ / / /  __/ /_  ",
            r"/_/ /_/\__,_/\__/\___/_/ /_/\___/\__/  {:>2}".format(
                "v" + __version__),
            r"",
            r"",
        ]

        return "\n".join(lines)

    def render_legend(self, dataframe):
        def render_label(index, low, high):
            metric_range = self.max_metric - self.min_metric

            return (
                self.colors.colormap[index]
                + "█ "
                + self.colors.end
                + "{:.2f}".format(low * metric_range + self.min_metric)
                + " - "
                + "{:.2f}".format(high * metric_range + self.min_metric)
                + "\n"
            )

        legend = (
            "\n"
            + "\033[4m"
            + "Legend"
            + self.colors.end
            + " (Metric: "
            + str(self.primary_metric)
            + " Min: {:.2f}".format(self.min_metric)
            + " Max: {:.2f}".format(self.max_metric)
            + ")\n"
        )

        legend += render_label(0, 0.9, 1.0)
        legend += render_label(1, 0.7, 0.9)
        legend += render_label(2, 0.5, 0.7)
        legend += render_label(3, 0.3, 0.5)
        legend += render_label(4, 0.1, 0.3)
        legend += render_label(5, 0.0, 0.1)

        legend += "\n" + \
            self._ansi_color_for_name("name") + "name" + self.colors.end
        legend += " User code    "

        legend += self.colors.left + self.lr_arrows["◀"] + self.colors.end
        legend += " Only in left graph    "
        legend += self.colors.right + self.lr_arrows["▶"] + self.colors.end
        legend += " Only in right graph\n"

        if self.annotation_column is not None:

            # extra-p model complexity analysis legend customization
            if "_complexity" in self.annotation_column:

                # get unique complexity classes from all models
                unique_complexity_classes = self.get_unique_complexity_classes(
                    dataframe)

                # add color coding for complexity classes to data frame
                color_map_dict = self.colormap_for_complexity_classes(
                    unique_complexity_classes)

                legend += "\n\033[4mLegend Complexity Classes" + \
                    self.colors.end

                for complexity_class in unique_complexity_classes:
                    legend += "\n" + color_map_dict[complexity_class] + u"█ " + \
                        self.colors.end + str(complexity_class)
                legend += "\n"

                # create a legend for the model parameters
                legend += "\n\033[4mLegend Model Parameters" + \
                    self.colors.end
                if self.modeler_config is None:
                    column_headers = list(dataframe.columns.values)
                else:
                    column_headers = list(
                        dataframe[self.modeler_config].columns.values)
                column_name = None
                for column in column_headers:
                    if "_extrap-model" in column and "AR2" not in column and "RE" not in column and "RSS" not in column and "SMAPE" not in column and "coefficient" not in column and "complexity" not in column and "growth_rank" not in column:
                        column_name = column
                        break
                if self.modeler_config is None:
                    model_wrapper_object = dataframe[column_name].iloc[0]
                else:
                    model_wrapper_object = dataframe[self.modeler_config][column_name].iloc[0]
                # Avg time/rank_extrap-model
                for i in range(len(model_wrapper_object.parameters)):
                    legend += "\n" + \
                        str(model_wrapper_object.default_param_names[i]) + " -> " + \
                        str(model_wrapper_object.parameters[i])

            # temporal pattern legend customization
            if "_pattern" in self.annotation_column:
                score_ranges = [0.0, 0.2, 0.4, 0.6, 1.0]
                legend += "\nTemporal Pattern"
                for k in self.temporal_symbols.keys():
                    if "none" not in k:
                        legend += "   " + self.temporal_symbols[k] + " " + k
                legend += "\nTemporal Score  "
                if self.colormap_annotations:
                    legend_color_mapping = sorted(score_ranges)
                    legend_colormap = ColorMaps().get_colors(
                        self.colormap_annotations, False
                    )
                    for i in range(len(score_ranges) - 1):
                        color = legend_colormap[
                            legend_color_mapping.index(score_ranges[i + 1])
                            % len(legend_colormap)
                        ]
                        legend += "{}".format(color)
                        legend += "   {} - {}".format(
                            score_ranges[i], score_ranges[i + 1]
                        )
                        legend += "{}".format(self.colors_annotations.end)
                else:  # no color map passed in
                    for i in range(len(score_ranges) - 1):
                        legend += "   {} - {}".format(
                            score_ranges[i], score_ranges[i + 1]
                        )

        return legend

    def render_frame(self, node, dataframe, indent="", child_indent=""):
        node_depth = node._depth
        if node_depth < self.depth:
            # set dataframe index based on whether rank and thread are part of
            # the MultiIndex
            if "rank" in dataframe.index.names and "thread" in dataframe.index.names:
                df_index = (node, self.rank, self.thread)
            elif "rank" in dataframe.index.names:
                df_index = (node, self.rank)
            elif "thread" in dataframe.index.names:
                df_index = (node, self.thread)
            else:
                df_index = node

            try:
                if self.modeler_config is not None and self.primary_metric not in dataframe.columns:
                    node_metric = dataframe[self.modeler_config].loc[df_index,
                                                                     self.primary_metric]
                else:
                    node_metric = dataframe.loc[df_index,
                                                self.primary_metric]
                if self.modeler_config is not None:
                    node_metric = float(node_metric)

                metric_precision = "{:." + str(self.precision) + "f}"
                metric_str = (
                    self._ansi_color_for_metric(node_metric)
                    + metric_precision.format(node_metric)
                    + self.colors.end
                )

                if self.second_metric is not None:
                    metric_str += " {c.faint}{second_metric:.{precision}f}{c.end}".format(
                        second_metric=dataframe.loc[df_index,
                                                    self.second_metric],
                        precision=self.precision,
                        c=self.colors,
                    )

                if self.annotation_column is not None:
                    if self.modeler_config is None:
                        annotation_content = str(
                            dataframe.loc[df_index, self.annotation_column]
                        )
                    else:
                        annotation_content = str(
                            dataframe[self.modeler_config].loc[df_index,
                                                               self.annotation_column]
                        )

                    # custom visualization for complexity class analysis with extra-p models
                    if "_complexity" in self.annotation_column:

                        # get unique complexity classes from all models
                        unique_complexity_classes = self.get_unique_complexity_classes(
                            dataframe)

                        # add color coding for complexity classes to data frame
                        color_map_dict = self.colormap_for_complexity_classes(
                            unique_complexity_classes)

                        metric_str += "{}".format(
                            color_map_dict[annotation_content])

                    # custom visualization for temporal pattern metrics if it is the annotation column
                    if "_pattern" in self.annotation_column:
                        self.temporal_symbols = {
                            "none": "",
                            "constant": "\U00002192",
                            "phased": "\U00002933",
                            "dynamic": "\U000021DD",
                            "sporadic": "\U0000219D",
                        }
                        pattern_metric = dataframe.loc[df_index,
                                                       self.annotation_column]
                        annotation_content = self.temporal_symbols[pattern_metric]
                        if self.colormap_annotations:
                            self.colors_annotations_mapping = list(
                                dataframe[self.annotation_column].apply(
                                    str).unique()
                            )
                            coloring_content = pattern_metric
                            if coloring_content != "none":
                                color_annotation = self.colors_annotations.colormap[
                                    self.colors_annotations_mapping.index(
                                        coloring_content)
                                    % len(self.colors_annotations.colormap)
                                ]
                                metric_str += " {}".format(color_annotation)
                                metric_str += "{}".format(annotation_content)
                                metric_str += "{}".format(
                                    self.colors_annotations.end)
                            else:
                                metric_str += "{}".format(annotation_content)
                        else:  # no colormap passed in
                            metric_str += " {}".format(annotation_content)

                    # no pattern column
                    elif self.colormap_annotations:
                        if isinstance(self.colormap_annotations, dict):
                            color_annotation = self.colors_annotations_mapping[
                                annotation_content
                            ]
                        else:
                            color_annotation = self.colors_annotations.colormap[
                                self.colors_annotations_mapping.index(
                                    annotation_content)
                                % len(self.colors_annotations.colormap)
                            ]
                        metric_str += " [{}".format(color_annotation)
                        metric_str += "{}".format(annotation_content)
                        metric_str += "{}]".format("\033[0m")

                    else:
                        if self.colormap_annotations:
                            if isinstance(self.colormap_annotations, dict):
                                color_annotation = self.colors_annotations_mapping[
                                    annotation_content
                                ]
                            else:
                                color_annotation = self.colors_annotations.colormap[
                                    self.colors_annotations_mapping.index(
                                        annotation_content)
                                    % len(self.colors_annotations.colormap)
                                ]
                            metric_str += " [{}".format(color_annotation)
                            metric_str += "{}".format(annotation_content)
                            metric_str += "{}]".format(
                                self.colors_annotations.end)

                        else:
                            metric_str += " [{}]".format(annotation_content)

                if self.modeler_config is None:
                    node_name = dataframe.loc[df_index, self.name]
                else:
                    node_name = dataframe[self.modeler_config].loc[df_index, self.name]
                if self.expand is False:
                    if len(node_name) > 39:
                        node_name = (
                            node_name[:18] + "..." +
                            node_name[(len(node_name) - 18):]
                        )
                name_str = (
                    self._ansi_color_for_name(
                        node_name) + node_name + self.colors.end
                )

                # 0 is "", 1 is "L", and 2 is "R"
                if "_missing_node" in dataframe.columns:
                    left_or_right = dataframe.loc[df_index, "_missing_node"]
                    if left_or_right == 0:
                        lr_decorator = ""
                    elif left_or_right == 1:
                        lr_decorator = " {c.left}{decorator}{c.end}".format(
                            decorator=self.lr_arrows["◀"], c=self.colors
                        )
                    elif left_or_right == 2:
                        lr_decorator = " {c.right}{decorator}{c.end}".format(
                            decorator=self.lr_arrows["▶"], c=self.colors
                        )

                result = "{indent}{metric_str} {name_str}".format(
                    indent=indent, metric_str=metric_str, name_str=name_str
                )
                if "_missing_node" in dataframe.columns:
                    result += lr_decorator
                if self.context in dataframe.columns:
                    result += u" {c.faint}{context}{c.end}\n".format(
                        context=dataframe.loc[df_index,
                                              self.context], c=self.colors
                    )
                else:
                    result += "\n"

                if self.unicode:
                    indents = {"├": "├─ ", "│": "│  ", "└": "└─ ", " ": "   "}
                else:
                    indents = {"├": "|- ", "│": "|  ", "└": "`- ", " ": "   "}

                # ensures that we never revisit nodes in the case of
                # large complex graphs
                if node not in self.visited:
                    self.visited.append(node)
                    sorted_children = sorted(
                        node.children, key=lambda n: n._hatchet_nid)
                    if sorted_children:
                        last_child = sorted_children[-1]

                    for child in sorted_children:
                        if child is not last_child:
                            c_indent = child_indent + indents["├"]
                            cc_indent = child_indent + indents["│"]
                        else:
                            c_indent = child_indent + indents["└"]
                            cc_indent = child_indent + indents[" "]
                        result += self.render_frame(
                            child, dataframe, indent=c_indent, child_indent=cc_indent
                        )

            except KeyError:
                result = ""
                indents = {"├": "", "│": "", "└": "", " ": ""}

        else:
            result = ""
            indents = {"├": "", "│": "", "└": "", " ": ""}

        return result

    def get_unique_complexity_classes(self, dataframe):
        unique_complexity_classes = []
        if self.modeler_config is None:
            for i in range(len(dataframe[self.annotation_column])):
                if str(dataframe[self.annotation_column].iloc[i]) not in unique_complexity_classes:
                    unique_complexity_classes.append(
                        str(dataframe[self.annotation_column].iloc[i]))
        else:
            for i in range(len(dataframe[self.modeler_config][self.annotation_column])):
                if str(dataframe[self.modeler_config][self.annotation_column].iloc[i]) not in unique_complexity_classes:
                    unique_complexity_classes.append(
                        str(dataframe[self.modeler_config][self.annotation_column].iloc[i]))
        return unique_complexity_classes

    def colormap_for_complexity_classes(self, unique_complexity_classes):
        color_map_dict = {}
        range_values = np.arange(
            0, 1, 1 / len(unique_complexity_classes))
        import matplotlib
        # chose the color map to take the colors from dynamically
        if self.colormap_annotations:
            if isinstance(self.colormap_annotations, str):
                colormap = self.colormap_annotations
        else:
            if len(unique_complexity_classes) > 20:
                colormap = "brg"
            else:
                colormap = "tab20b"
        if colormap != "black":
            cmap = matplotlib.cm.get_cmap(colormap)
            for i in range(len(range_values)):
                red = int(cmap(range_values[i])[0] / (1 / 255))
                green = int(cmap(range_values[i])[1] / (1 / 255))
                blue = int(cmap(range_values[i])[2] / (1 / 255))
                ansi_color_str = (
                    "\033[38;2;"
                    + str(red)
                    + ";"
                    + str(green)
                    + ";"
                    + str(blue)
                    + "m"
                )
                color_map_dict[unique_complexity_classes[i]
                               ] = ansi_color_str
        else:
            for i in range(len(range_values)):
                ansi_color_str = (
                    "\033[38;2;"
                    + str(0)
                    + ";"
                    + str(0)
                    + ";"
                    + str(0)
                    + "m"
                )
                color_map_dict[unique_complexity_classes[i]
                               ] = ansi_color_str

        return color_map_dict

    def _ansi_color_for_metric(self, metric):
        metric_range = self.max_metric - self.min_metric

        if metric_range != 0:
            proportion_of_total = (metric - self.min_metric) / metric_range
        else:
            proportion_of_total = metric / 1

        if proportion_of_total > 0.9:
            return self.colors.colormap[0]
        elif proportion_of_total > 0.7:
            return self.colors.colormap[1]
        elif proportion_of_total > 0.5:
            return self.colors.colormap[2]
        elif proportion_of_total > 0.3:
            return self.colors.colormap[3]
        elif proportion_of_total > 0.1:
            return self.colors.colormap[4]
        elif proportion_of_total >= 0:
            return self.colors.colormap[5]
        else:
            return self.colors.blue

    def _ansi_color_for_name(self, node_name):
        if self.highlight is False:
            return ""

        if "<unknown procedure>" in node_name or "<unknown file>" in node_name:
            return ""
        else:
            return self.colors.bg_white_255 + self.colors.dark_gray_255

    class colors_enabled:
        colormap = []

        blue = "\033[34m"
        cyan = "\033[36m"

        bg_white_255 = "\033[48;5;246m"
        dark_gray_255 = "\033[38;5;232m"

        left = "\033[38;5;160m"
        right = "\033[38;5;28m"

        faint = "\033[2m"
        end = "\033[0m"

    class colors_disabled:
        colormap = ["", "", "", "", "", "", ""]

        def __getattr__(self, key):
            return ""

    colors_disabled = colors_disabled()
