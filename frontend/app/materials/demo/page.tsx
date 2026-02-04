'use client';

import MaterialViewer from "../../../components/material/MaterialViewer";

const DEMO_CONTENT = [
  "Binary search is a divide-and-conquer algorithm.",
  "It works on sorted arrays by repeatedly halving the search space.",
  "The time complexity of binary search is O(log n).",
  "Binary search relies on the invariant that the array is sorted.",
  "Incorrect mid calculation can cause overflow in some languages.",
].join("\n\n");

export default function DemoMaterialPage() {
  return (
    <MaterialViewer materialId="demo-material" userId="demo-user" content={DEMO_CONTENT} />
  );
}
