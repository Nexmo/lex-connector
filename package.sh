#!/bin/bash

ARGS=$(getopt --options p::b:c: --long push::,branch:,commit: --name "$0" -- "$@")

# If parsing of option failed, exit
if [ $? -ne 0 ];
then
    exit 1
fi

eval set -- "$ARGS";

# default values
DEB_REPO=
GIT_BRANCH=
GIT_COMMIT=
PACKAGING_CONF=conf/deb
PACKAGING_CONF_TEMPLATE=conf/deb.template

while true; do
    case "$1" in
	-p|--push)
	    case "$2" in
		"")
		# Using default repository (on QA = qaservice1)
		    DEB_REPO=qaservice1.internal
		    ;;
		*)
		    DEB_REPO="$2"
		    ;;
	    esac
	    shift 2;
	    ;;
	-b|--branch)
	    GIT_BRANCH="$2"
	    shift 2;
	    ;;
	-c|--commit)
	    GIT_COMMIT="$2"
	    shift 2;
	    ;;
	--)
	    shift;
	    break;
	    ;;
	*)
	    echo "Unmanaged option $1"
	    shift 1;
	    ;;
    esac
done


if [ "$GIT_BRANCH" == "" -o "$GIT_COMMIT" == "" ]
then
    echo "Please specify the branch and commit hash (informations required to compute the version of the package)"
    exit 3
fi

echo "Creating and pushing to $DEB_REPO the package for ${GIT_BRANCH}@${GIT_COMMIT}"

# Get date of branch / commit
declare -r commit_date=$(git show -s --format=format:"%ci" $GIT_COMMIT)
declare -r commit_date_format=$(date -d "${commit_date}" +%Y%m%d.%H%M%S.000)
declare -r escaped_git_branch=$(sed -r 's/[^A-Za-z0-9.+:~-]/-/g' <<< ${GIT_BRANCH})
declare -r package_version="${commit_date_format}+${escaped_git_branch}+${GIT_COMMIT:0:7}"
echo "Version will be ${package_version}"

DIR=$(dirname $(realpath $0))
pushd $DIR/.nexmopkg >/dev/null

sed "s/##VERSION##/$package_version/" $PACKAGING_CONF_TEMPLATE > $PACKAGING_CONF
make clean deb

if [ "$DEB_REPO" == "" ]
then
    echo "Package created but not pushed"
else
    echo "Pushing packages"
    # Get the name of the debian package created and check if already pushed (meaning we have committed a version with same version as previous commit)
    package_already_pushed() {
        declare -r package="$1"
        echo "It looks like the package we have just created ($package) has already been pushed qith that revision to the debian repository so let's not push it again and break the checksums"
        exit 13
    } 
    pushd build >> /dev/null
    declare -r deb_package=$(ls -rt nexmo-lexconnector*.deb)
    ssh -i /var/lib/jenkins/.ssh/nexmo-ops.pem jenkinsdeploy@${DEB_REPO} cat /var/debrepo/debian/stable/amd64/Packages | egrep "Filename: .*/${deb_package}" && package_already_pushed "${deb_package}"
    
    # Pushing files to the debian repository
    echo scp -i /var/lib/jenkins/.ssh/nexmo-ops.pem nexmo-lexconnector*.deb nexmo-lexconnector*.changes jenkinsdeploy@${DEB_REPO}:/var/debrepo/incoming || exit 14
    popd > /dev/null
fi

popd > /dev/null

exit 0
