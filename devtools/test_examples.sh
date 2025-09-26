# Get all subfolders
mapfile -t folders < <(find . -maxdepth 1 -mindepth 1 -type d ! -name ".*")

# Set NEST_FOLDER variable in case it is not set
if [ -z "$NEST_FOLDER" ]; then
  SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
  export NEST_FOLDER="$(dirname $SCRIPT_DIR)/.nx/installation/nest";
fi

length=${#folders[@]}
# For each subfolder, run unittests
output_results=()
for ((i=0; i<length; i++)); do
  folder=${folders[i]}
  cd "$folder" || exit 1
  # if example folder contains nest in the title, install also NEST
  if [[ $folder == *"nest"* ]]; then
    echo "Installing NEST"
    uv pip install cmake cython~=3.0.12
    script="../$( dirname -- "${BASH_SOURCE[0]:-$0}"; )/install-nest.sh"
    echo "Running $script"
    uv run bash $script > /dev/null
    if [ $? -ne 0 ]; then
      output_results+=("1")
      cd .. || exit 1
      continue
    fi
  fi
  uv sync
  echo "Running unittests for $folder"
  uv run python -m unittest discover -v -s tests
  output_results+=("$?")
  cd .. || exit 1
done


failed=0
for ((i=0; i<length; i++)); do
  if [ ${output_results[i]} -ne 0 ]; then
    result="FAILED";
    failed=1
  else
    result="PASSED";
  fi
  folder=${folders[i]}
  echo "$folder unittests: $result"
done

exit $failed