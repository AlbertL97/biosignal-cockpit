import { useMemo } from "react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { AppFrame, type RailItem } from "@/components/layout";
import { Dashboard } from "@/pages/Dashboard";
import { DomainReport } from "@/pages/DomainReport";
import { Genome } from "@/pages/Genome";
import { GenomeTrait } from "@/pages/GenomeTrait";

const NAV: RailItem[] = [
  { id: "overview", label: "Overview", icon: "◎" },
  { id: "genome", label: "Genome", icon: "⌬" },
];

/** Map the current pathname to the active nav rail id. */
function activeNavFor(pathname: string): string {
  if (pathname.startsWith("/genome")) return "genome";
  return "overview";
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const active = useMemo(() => activeNavFor(location.pathname), [location.pathname]);

  const onNavSelect = (id: string) => {
    if (id === "genome") navigate("/genome");
    else navigate("/");
  };

  return (
    <AppFrame
      navItems={NAV}
      activeNavId={active}
      onNavSelect={onNavSelect}
      statusLine="Personal health intelligence · local-first"
    >
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/domain/:id" element={<DomainReport />} />
        <Route path="/genome" element={<Genome />} />
        <Route path="/genome/:id" element={<GenomeTrait />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppFrame>
  );
}
