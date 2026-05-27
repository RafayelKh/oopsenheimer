import { SimulationStatusView } from "@/components/SimulationStatusView";

type SimulationPageProps = {
  params: Promise<{ id: string }>;
};

export default async function SimulationPage({ params }: SimulationPageProps) {
  const { id } = await params;

  return (
    <main className="page grid">
      <SimulationStatusView simulationId={id} />
    </main>
  );
}
