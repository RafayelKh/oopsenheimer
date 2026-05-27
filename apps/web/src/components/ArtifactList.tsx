import { artifactDownloadUrl } from "@/lib/api";

type ArtifactListProps = {
  simulationId?: string;
  artifacts?: string[];
};

const pendingArtifacts = ["scene.inp", "scene.vxl", "scene.map.json", "scene.meta.json"];

export function ArtifactList({ simulationId, artifacts = pendingArtifacts }: ArtifactListProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <strong>Արտեֆակտներ</strong>
        <span className="muted">{simulationId ?? "սպասում է"}</span>
      </div>
      <div className="panel-body artifact-list">
        {artifacts.map((artifact) => (
          <div className="artifact-row" key={artifact}>
            {simulationId ? (
              <a href={artifactDownloadUrl(simulationId, artifact)} target="_blank" rel="noreferrer">
                {artifact}
              </a>
            ) : (
              artifact
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
