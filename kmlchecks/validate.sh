#!/bin/bash
#
# validate.sh - validate one or more KML files.
#
# usage:
#    ./validate.sh a.kml [b.kml [...]]

# download xsd files if necessary
if [[ ! -e kml22gx.xsd ]]; then
   wget https://code.google.com/apis/kml/schema/kml22gx.xsd
fi

if [[ ! -e ogckml22.xsd ]]; then
   wget https://schemas.opengis.net/kml/2.2.0/ogckml22.xsd
fi

for x in $*; do
   xmllint --noout \
         --schema ogckml22.xsd \
         --schema kml22gx.xsd \
         $x
done
