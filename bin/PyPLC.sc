#!/bin/bash

# This script is a variant from TangoScripts/tango_pyds
# srubio@cells.es, 2016

DS=$(basename $0)

if [ $(echo $1 | grep "/" ) ] ; then
 IFS='/' read -r DS INSTANCE <<< "$1"
else
 DS=$(basename $0)
 INSTANCE=$1
fi

DSORB=$(python -c "import PyTango;print(PyTango.Database().get_property('ORBendPoint',['${DS}/${INSTANCE}']).values()[0][0])" 2>/dev/null)
if [ "$DSORB" ] ; then
 DSORB="-ORBendPoint $DSORB"
fi

DSPATH=$(python -c "import imp;print(imp.find_module('${DS}')[1])" 2>/dev/null)

if [ ! "$DSPATH" ] ; then
 DSPATH=$(python -c "import imp;print(imp.find_module('fandango')[1])")
 if [ -e "$DSPATH/device/$DS.py" ] ; then
  DSPATH=$DSPATH/device
 elif [ -e "$DSPATH/interface/$DS.py" ] ; then
  DSPATH=$DSPATH/interface
 fi
fi

DSPATH=$(readlink -f $DSPATH)

echo "Launching $DSPATH/$DS $INSTANCE at $DSORB"

# TODO: if it is mandatory to be in the module path 
cd ${DSPATH}

if [ $(which screen 2>/dev/null) ] ; then
 if [ ! "$(echo $* | grep attach)" ] ; then
  echo "run detached"
  CMD="screen -dm -S $DS-$INSTANCE "
 else
  CMD="screen -S $DS-$INSTANCE "
 fi
else
  CMD=""
fi

CMD="${CMD} python ${DSPATH}/$DS.py $INSTANCE $2 $DSORB"
echo $CMD
$CMD
