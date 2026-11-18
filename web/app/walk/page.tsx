import { BoundaryWalker } from "./boundary-walker";

export const metadata = {
  title: "田界步行 · ほ場ウォーク · Boundary walk",
};

export default function WalkPage() {
  return (
    <main style={{ maxWidth: "32rem", margin: "0 auto", padding: "1.5rem 1.2rem 4rem" }}>
      <BoundaryWalker />
    </main>
  );
}
