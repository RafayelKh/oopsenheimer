import { SceneWorkspace } from "@/components/SceneWorkspace";

type ScenePageProps = {
  params: Promise<{ id: string }>;
};

export default async function ScenePage({ params }: ScenePageProps) {
  const { id } = await params;

  return (
    <main className="page grid">
      <SceneWorkspace sceneId={id} />
    </main>
  );
}
