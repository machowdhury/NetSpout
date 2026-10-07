import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const safeComponent = (value: string) => {
  const cleaned = value.replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '');
  if (!cleaned || cleaned === '.' || cleaned === '..') {
    throw new Error(`Invalid artifact path component: ${JSON.stringify(value)}`);
  }
  return cleaned;
};

export const testArtifactRoot = () => {
  const configured = process.env.NETSPOUT_TEST_ARTIFACT_ROOT;
  if (configured) {
    const destination = path.resolve(configured);
    const repository = path.resolve(process.cwd(), '..');
    const protectedRoots = [
      'catalog',
      'backend/app/catalog_data',
      'netspout/catalog',
      'netspout/bin/catalog_data',
      'netspout/bin/netspout_core/catalog_data',
      'docs/acceptance',
      'docs/implementation/images',
    ].map((item) => path.join(repository, item));
    if (protectedRoots.some((root) =>
      destination === root || destination.startsWith(`${root}${path.sep}`))) {
      throw new Error(
        `NETSPOUT_TEST_ARTIFACT_ROOT must not target accepted evidence: ${destination}`,
      );
    }
    return destination;
  }
  return path.join(
    os.tmpdir(),
    'netspout-test-artifacts',
    'temporary',
    `process-${process.pid}`,
  );
};

export const artifactPath = (
  suite: string,
  name: string,
  category = 'screenshots',
) => {
  const directory = path.join(
    testArtifactRoot(),
    safeComponent(category),
    safeComponent(suite),
  );
  fs.mkdirSync(directory, { recursive: true });
  return path.join(directory, safeComponent(name));
};
