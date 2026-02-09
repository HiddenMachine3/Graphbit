'use client';

import { useEffect, useState } from "react";

import MaterialViewer from "../../../components/material/MaterialViewer";
import Loading from "../../../components/Loading";
import ErrorState from "../../../components/ErrorState";
import { fetchMaterial, listMaterials } from "../../../lib/api/material";
import { getCurrentSession, startSession } from "../../../lib/api/session";

type MaterialContent = {
  id: string;
  title: string;
  chunks: string[];
};

export default function DemoMaterialPage() {
  const [material, setMaterial] = useState<MaterialContent | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const session = (await getCurrentSession()) ?? (await startSession());
        if (mounted) {
          setUserId(session.user_id);
        }

        const materials = await listMaterials();
        if (materials.length === 0) {
          throw new Error("No materials available");
        }
        const selected = await fetchMaterial(materials[0].id);
        if (mounted) {
          setMaterial(selected);
        }
      } catch (err) {
        if (mounted) {
          const message = err instanceof Error ? err.message : "Failed to load material";
          setError(message);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return <Loading />;
  }

  if (error || !material || !userId) {
    return <ErrorState message={error ?? "Material unavailable"} />;
  }

  return (
    <MaterialViewer
      materialId={material.id}
      userId={userId}
      content={material.chunks.join("\n\n")}
    />
  );
}
