import Link from "next/link";
import { zh } from "@/lib/i18n/zh";

const LAYER_LINKS = {
  l1: [
    { href: "/strategy/diagnosis", label: zh.strategy.tabs.diagnosis },
    { href: "/strategy/probes", label: zh.strategy.tabs.probes },
    { href: "/strategy/visibility", label: zh.strategy.tabs.visibility },
    { href: "/strategy/scene-graph", label: zh.strategy.tabs.sceneGraph },
    { href: "/strategy/theme-mining", label: zh.strategy.tabs.themeMining },
    { href: "/strategy/reports", label: zh.strategy.tabs.reports },
  ],
  l2: [
    { href: "/production/tasks", label: zh.production.tabs.tasks },
    { href: "/production/ai_config", label: zh.production.tabs.ai_config },
    { href: "/production/materials", label: zh.production.tabs.materials },
    { href: "/production/knowledge", label: zh.production.tabs.knowledge },
    { href: "/production/geo-eval", label: zh.production.tabs["geo-eval"] },
  ],
  l3: [
    { href: "/operations/articles", label: zh.operations.tabs.articles },
    { href: "/operations/distribution/tasks", label: zh.distribution.tasksTab },
    { href: "/operations/distribution", label: zh.operations.tabs.distribution },
    { href: "/operations/analytics", label: zh.operations.tabs.analytics },
  ],
};

export function LayerCards() {
  return (
    <section className="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-3">
      <LayerCard
        href="/strategy/diagnosis"
        label={zh.dashboard.layers.l1Label}
        title={zh.dashboard.layers.l1Title}
        desc={zh.dashboard.layers.l1Desc}
        tone="violet"
        links={LAYER_LINKS.l1}
      />
      <LayerCard
        href="/production/overview"
        label={zh.dashboard.layers.l2Label}
        title={zh.dashboard.layers.l2Title}
        desc={zh.dashboard.layers.l2Desc}
        tone="emerald"
        links={LAYER_LINKS.l2}
      />
      <LayerCard
        href="/operations/overview"
        label={zh.dashboard.layers.l3Label}
        title={zh.dashboard.layers.l3Title}
        desc={zh.dashboard.layers.l3Desc}
        tone="blue"
        links={LAYER_LINKS.l3}
      />
    </section>
  );
}

function LayerCard({
  href,
  label,
  title,
  desc,
  tone,
  links,
}: {
  href: string;
  label: string;
  title: string;
  desc: string;
  tone: "violet" | "emerald" | "blue";
  links: { href: string; label: string }[];
}) {
  const border = {
    violet: "border-violet-200 bg-violet-50/60 hover:border-violet-300",
    emerald: "border-emerald-200 bg-emerald-50/60 hover:border-emerald-300",
    blue: "border-blue-200 bg-blue-50/60 hover:border-blue-300",
  }[tone];
  const labelColor = {
    violet: "text-violet-700",
    emerald: "text-emerald-700",
    blue: "text-blue-700",
  }[tone];
  const linkColor = {
    violet: "text-violet-800",
    emerald: "text-emerald-800",
    blue: "text-blue-800",
  }[tone];

  return (
    <div className={`group relative rounded-lg border p-5 transition hover:shadow-sm ${border}`}>
      <Link href={href} className="absolute inset-0 rounded-lg" aria-label={title} />
      <p className={`text-xs font-semibold uppercase tracking-wide ${labelColor}`}>{label}</p>
      <h2 className="mt-2 text-lg font-semibold text-gray-900">{title}</h2>
      <p className="mt-2 text-sm text-gray-600">{desc}</p>
      <div className="relative z-10 mt-4 flex flex-wrap gap-2">
        {links.map((link) => (
          <Link key={link.href} href={link.href} className={`text-sm font-medium hover:underline ${linkColor}`}>
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
