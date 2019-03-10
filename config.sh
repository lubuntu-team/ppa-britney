export LP_TEAM="lubuntu-ci"
export SOURCE_PPA="unstable-ci-proposed"
export SOURCE_PPA_URL="http://ppa.launchpad.net/$LP_TEAM/$SOURCE_PPA/ubuntu/dists/$RELEASE/main"
export DEST_PPA="unstable-ci"
export DEST_PPA_URL="http://ppa.launchpad.net/$LP_TEAM/$DEST_PPA/ubuntu/dists/$RELEASE/main"

export MAIN_ARCHIVE="http://archive.ubuntu.com/ubuntu/dists"
export PORTS_ARCHIVE="http://ports.ubuntu.com/dists"
export ARCHES="i386 amd64"
export PORTS_ARCHES="armhf arm64 ppc64el s390x"

export BRITNEY_LOC="britney2-ubuntu/britney.py"
export BRITNEY_DATADIR="britney_data"
export BRITNEY_OUTDIR="britney_output"
export BRITNEY_HINTDIR="britney_hints"
export BRITNEY_CACHE="britney_cache"
export BRITNEY_TIMESTAMP=$(date +'%Y%m%d%H%M')
