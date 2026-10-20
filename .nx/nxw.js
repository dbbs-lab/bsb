"use strict";
// This file should be committed to your repository! It wraps Nx and ensures
// that your local installation matches nx.json.
// See: https://nx.dev/recipes/installation/install-non-javascript for more info.




Object.defineProperty(exports, "__esModule", { value: true });
const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const installationPath = path.join(__dirname, 'installation', 'package.json');
function matchesCurrentNxInstall(currentInstallation, nxJsonInstallation) {
    if (!currentInstallation.devDependencies ||
        !Object.keys(currentInstallation.devDependencies).length) {
        return false;
    }
    try {
        if (currentInstallation.devDependencies['nx'] !==
            nxJsonInstallation.version ||
            require(path.join(path.dirname(installationPath), 'node_modules', 'nx', 'package.json')).version !== nxJsonInstallation.version) {
            return false;
        }
        for (const [plugin, desiredVersion] of Object.entries(nxJsonInstallation.plugins || {})) {
            if (currentInstallation.devDependencies[plugin] !== desiredVersion) {
                return false;
            }
        }
        return true;
    }
    catch {
        return false;
    }
}
function ensureDir(p) {
    if (!fs.existsSync(p)) {
        fs.mkdirSync(p, { recursive: true });
    }
}
function getCurrentInstallation() {
    try {
        return require(installationPath);
    }
    catch {
        return {
            name: 'nx-installation',
            version: '0.0.0',
            devDependencies: {},
        };
    }
}
function performInstallation(currentInstallation, nxJson) {
    fs.writeFileSync(installationPath, JSON.stringify({
        name: 'nx-installation',
        devDependencies: {
            nx: nxJson.installation.version,
            ...nxJson.installation.plugins,
        },
    }));
    try {
        cp.execSync('npm i', {
            cwd: path.dirname(installationPath),
            stdio: 'inherit',
            windowsHide: false,
        });
    }
    catch (e) {
        // revert possible changes to the current installation
        fs.writeFileSync(installationPath, JSON.stringify(currentInstallation));
        // rethrow
        throw e;
    }
}
function ensureUpToDateInstallation() {
    const nxJsonPath = path.join(__dirname, '..', 'nx.json');
    let nxJson;
    try {
        nxJson = require(nxJsonPath);
        if (!nxJson.installation) {
            console.error('[NX]: The "installation" entry in the "nx.json" file is required when running the nx wrapper. See https://nx.dev/recipes/installation/install-non-javascript');
            process.exit(1);
        }
    }
    catch {
        console.error('[NX]: The "nx.json" file is required when running the nx wrapper. See https://nx.dev/recipes/installation/install-non-javascript');
        process.exit(1);
    }
    try {
        ensureDir(path.join(__dirname, 'installation'));
        const currentInstallation = getCurrentInstallation();
        if (!matchesCurrentNxInstall(currentInstallation, nxJson.installation)) {
            performInstallation(currentInstallation, nxJson);
        }
    }
    catch (e) {
        const messageLines = [
            '[NX]: Nx wrapper failed to synchronize installation.',
        ];
        if (e instanceof Error) {
            messageLines.push('');
            messageLines.push(e.message);
            messageLines.push(e.stack);
        }
        else {
            messageLines.push(e.toString());
        }
        console.error(messageLines.join('\n'));
        process.exit(1);
    }
}
if (!process.env.NX_WRAPPER_SKIP_INSTALL) {
    ensureUpToDateInstallation();
}

// @nxlv/python (23.x) decides whether a local dependency already carries a version
// with a regex that accepts neither extras nor environment markers, so at publish time
// `nmodl-glia[neuron]~=8.0` or `nrn-patch~=8.0 ; sys_platform != 'win32'` get
// `==<version>` appended, and PyPI rejects the result (it broke the 8.0.0 release).
// Widen the regex until upstream fixes it; only `.test()` is called on it.
function patchNxlvVersionRange() {
    const resolver = path.join(__dirname, 'installation', 'node_modules', '@nxlv', 'python', 'dist', 'provider', 'uv', 'build', 'resolvers', 'project.js');
    const broken = 'const VERSION_RANGE_REGEX = /^([a-zA-Z0-9._-]+)\\s*(==|!=|~=|===|>=|<=|>|<)\\s*([^\\s,;]+)(?:,?\\s*(==|!=|~=|===|>=|<=|>|<)\\s*([^\\s,;]+))*$/;';
    const fixed = 'const VERSION_RANGE_REGEX = /^([a-zA-Z0-9._-]+)\\s*(?:\\[[^\\]]*\\])?\\s*(==|!=|~=|===|>=|<=|>|<)\\s*([^\\s,;]+)(?:\\s*,?\\s*(==|!=|~=|===|>=|<=|>|<)\\s*([^\\s,;]+))*\\s*(?:;.*)?$/;';
    let source;
    try {
        source = fs.readFileSync(resolver, 'utf-8');
    }
    catch {
        return;
    }
    if (source.includes(fixed)) {
        return;
    }
    if (source.includes(broken)) {
        fs.writeFileSync(resolver, source.replace(broken, fixed));
        return;
    }
    console.warn('[NX]: Could not patch @nxlv/python VERSION_RANGE_REGEX: the code it targets changed. ' +
        'Check whether upstream fixed extras/markers in local dependency pins, then remove this patch from .nx/nxw.js.');
}
patchNxlvVersionRange();

// Resolve the CLI entrypoint from nx's own manifest rather than a fixed path:
// nx moved its bin from `bin/nx` to `dist/bin/nx.js` in v23.
const nxPackageDir = path.join(__dirname, 'installation', 'node_modules', 'nx');
const nxBin = require(path.join(nxPackageDir, 'package.json')).bin;
require(path.join(nxPackageDir, typeof nxBin === 'string' ? nxBin : nxBin.nx));
