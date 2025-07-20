# Get Nest installation folder
if [ -z "$NEST_FOLDER" ]; then
  SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
  NEST_FOLDER="$(dirname "$(dirname $SCRIPT_DIR)")/.nx/installation/nest";
fi
# Get NEST version
if [ -z "$NEST_VERSION" ]; then NEST_VERSION="3.7"; fi

# Check if NEST has been already installed
if [ "$(which nest)" != "" ];  then
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

# Install bsb-nest NEST dependency GSL
apt install libgsl-dev -y

# Checkout NEST version
cd "$NEST_FOLDER"
git checkout tags/v"$NEST_VERSION"
mkdir -p build
cd build

cmake .. -Dwith-mpi=ON

make install
