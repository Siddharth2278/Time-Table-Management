import { useStore } from "../store/useStore";
import { PageHeader, Card, CardContent, Button, Input, Label, Select } from "../components/ui";

export default function Settings() {
  const settings = useStore((s) => s.settings);
  const updateSettings = useStore((s) => s.updateSettings);

  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader title="Settings" description="College identity and theme. Stored in memory (offline)." />
      <Card><CardContent>
        <form
          onSubmit={(e) => e.preventDefault()}
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
        >
          <div><Label>College Name</Label><Input value={settings.college_name} onChange={(e) => updateSettings({ college_name: e.target.value })} /></div>
          <div><Label>Department</Label><Input value={settings.department} onChange={(e) => updateSettings({ department: e.target.value })} /></div>
          <div><Label>Academic Year</Label><Input value={settings.academic_year} onChange={(e) => updateSettings({ academic_year: e.target.value })} /></div>
          <div>
            <Label>Theme</Label>
            <Select value={settings.theme} onChange={(e) => updateSettings({ theme: e.target.value as "light" | "dark" })}>
              <option value="light">Light — archival cream</option>
              <option value="dark">Dark — off-black</option>
            </Select>
          </div>
          <div className="flex items-end"><Button type="submit">Saved automatically</Button></div>
        </form>
      </CardContent></Card>
    </div>
  );
}
