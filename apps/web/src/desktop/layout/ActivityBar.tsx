"use client";

import {
  Cpu, Activity, Brain, Wrench, Container, GitBranch, Zap, Wifi,
} from "lucide-react";

interface StatusChipProps {
  label: string;
  status: "green" | "yellow" | "red";
  icon: React.ReactNode;
  detail?: string;
}

function StatusChip({ label, status, icon, detail }: StatusChipProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 cursor-default"
      title={detail}
    >
      <span className={`status-dot ${status}`} />
      <span>{label}</span>
    </span>
  );
}

export function ActivityBar() {
  return (
    <div className="activity-bar">
      <div className="flex items-center gap-4">
        <StatusChip label="Planner" status="green" icon={<Activity size={10} />} detail="Planner: ready" />
        <StatusChip label="Executor" status="green" icon={<Zap size={10} />} detail="Executor: ready" />
        <StatusChip label="Memory" status="green" icon={<Brain size={10} />} detail="Memory: connected" />
        <StatusChip label="Skills" status="green" icon={<Wrench size={10} />} detail="Skills: 4 loaded" />
        <StatusChip label="Ollama" status="green" icon={<Cpu size={10} />} detail="Ollama: localhost:11434" />
        <StatusChip label="Gateway" status="green" icon={<Wifi size={10} />} detail="Gateway: localhost:8080" />
      </div>
      <div className="flex items-center gap-4">
        <StatusChip label="CPU 14%" status="green" icon={null} />
        <StatusChip label="Docker" status="green" icon={<Container size={10} />} detail="Docker: available" />
        <StatusChip label="main" status="green" icon={<GitBranch size={10} />} detail="Git: main branch" />
      </div>
    </div>
  );
}
