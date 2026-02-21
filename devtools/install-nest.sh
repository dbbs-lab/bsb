# Get Nest installation folder
if [ -z "$NEST_FOLDER" ]; then
  SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
  NEST_FOLDER="$(dirname $SCRIPT_DIR)/.nx/installation/nest";
fi
# Get NEST version
if [ -z "$NEST_VERSION" ]; then NEST_VERSION="3.7"; fi

# Trying to load NEST
INSTALLATION_FOLDER="$NEST_FOLDER/install"
if [ -f "$INSTALLATION_FOLDER/bin/nest_vars.sh" ]; then
  . "$INSTALLATION_FOLDER/bin/nest_vars.sh"
fi

# Lock check and installation to prevent concurrent file edition
LOCK_FILE="/tmp/bsb-nest.lock"
# Remove lock file on exit
trap 'rm -f "$LOCK_FILE"' EXIT
# Wait to be able to create file
while [ -f "$LOCK_FILE" ]; do sleep 1; done
touch "$LOCK_FILE"

# Check if NEST has been already installed
if [ "$(which nest)" == "$INSTALLATION_FOLDER/bin/nest" ];  then
  INSTALLED_VERSION=$(echo $(nest --version) | grep -o -E 'version [0-9.]+' | sed 's/version //')
  if [ "$INSTALLED_VERSION" == "$NEST_VERSION.0" ] || [ "$INSTALLED_VERSION" == "$NEST_VERSION" ]; then
    echo "NEST already installed.";
    exit 0;
  fi
fi

# Need to (re-)install NEST
# Clone nest repository if needed
if [ ! -d "$NEST_FOLDER" ]; then
  git clone https://github.com/nest/nest-simulator $NEST_FOLDER
fi

# Checkout NEST version
cd "$NEST_FOLDER" || exit 1
git checkout tags/v"$NEST_VERSION"
rm -rf build
rm -rf $INSTALLATION_FOLDER
mkdir build
cd build || exit 1

cmake .. -Dwith-mpi=ON -DCMAKE_INSTALL_PREFIX=$INSTALLATION_FOLDER

make install
exit 0;
