# zoterotags

This is an adapted version of the [Zotero Meta-Analysis Toolkit](https://github.com/DriedFishMatters/zotero-meta-analysis-toolkit) developed by the Dried Fish Matters project. The tool operates on a Zotero database, using the pyzotero API, to obtain basic quantitative measures about the distribution of references according to user-applied thematic tags and supply results in the form of an html table or bar graph.

This program is intended to be run on a web server as a cgi script. If invoked without any URL arguments, a user form will be returned inviting input parameter selection. See the [live version of this script on the DFM website](https://driedfishmatters.org/cgi-bin/zoterotags.py).

Unlike the original command line tool, this program caches data to reduce the number of API requests made to the Zotero server. To clear data you can use the URL parameters `purge_data=on` (purges cached query responses), `purge_images=on` (purges generated graph image files), or `purge=on` (purges both query results and graphs).

## Copying

Copyright 2021, Eric Thrift

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

## Credits

This script was originally written for the 
[Dried Fish Matters](https://driedfishmatters.org) project, supported 
by the [Social Sciences and Humanities Research Council of 
Canada](http://sshrc-crsh.gc.ca).
