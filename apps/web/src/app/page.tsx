import { LoadDemoPanel } from "@/components/LoadDemoPanel";
import { VoxelEditor } from "@/components/VoxelEditor";

export default function HomePage() {
  return (
    <main className="workbench-page">
      <VoxelEditor />
      <LoadDemoPanel />
    </main>
  );
}
