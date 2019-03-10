# Copyright 2014 Canonical Ltd.
# Author: Colin Watson <cjwatson@ubuntu.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Show charts using YUI."""

from textwrap import dedent


def make_chart_header(chart_name="chart", width=960, height=550):
    """Return HTML to declare the chart style and load YUI.

    This should be included in the <head> element.
    """
    params = {"chart_name": chart_name, "width": width, "height": height}
    return dedent("""\
        <style type="text/css">
            #%(chart_name)s {
                width: %(width)dpx;
                height: %(height)dpx;
            }
        </style>
        <script src="http://yui.yahooapis.com/3.17.2/build/yui/yui-min.js">
        </script>
        """) % params


def make_chart(source, keys, chart_name="chart"):
    """Return HTML to render a chart."""
    params = {
        "source": source,
        "chart_name": chart_name,
        "series_keys": ", ".join('"%s"' % key for key in keys),
        "series_styles": ", ".join(
            '"%s": { line: { weight: "2mm" } }' % key for key in keys),
        "series_schema_fields": ", ".join(
            '{key: "%s", parser: parseNum}' % key for key in keys),
        }
    return dedent("""\
        <div id="%(chart_name)s"></div>
        <script>
        YUI().use(['charts-legend', 'datasource'], function (Y) {
            var chart = new Y.Chart({
                dataProvider: [],
                render: "#%(chart_name)s",
                styles: {
                    axes: {
                        time: {
                            label: { rotation: -45, color: "#000000" }
                        },
                        values: {
                            label: { color: "#000000" },
                            alwaysShowZero: true,
                            scaleType: "logarithmic"
                        }
                    },
                    series: {
                        %(series_styles)s
                    }
                },
                categoryKey: "time",
                categoryType: "time",
                valueAxisName: "values",
                seriesKeys: [ %(series_keys)s ],
                showMarkers: false,
                legend: { position: "bottom" }
            });

            var parseDate = function (val) { return new Date(+val); };
            var parseNum = function (val) { return +val; };

            var csv = new Y.DataSource.IO({source: "%(source)s"});
            csv.plug(Y.Plugin.DataSourceTextSchema, {
                schema: {
                    resultDelimiter: "\\n",
                    fieldDelimiter: ",",
                    resultFields: [
                        {key: "time", parser: parseDate},
                        %(series_schema_fields)s
                    ]}});
            csv.sendRequest({request: "", on: {
                success: function (e) {
                    e.response.results.shift();  // remove CSV header
                    chart.set("dataProvider", e.response.results);
                },
                failure: function (e) {
                    console.log("Failed to fetch %(source)s: " +
                                e.error.message);
                }}});
        });
        </script>
        """) % params
