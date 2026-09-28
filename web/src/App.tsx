import { createBrowserRouter, RouterProvider } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import Timetable from "./pages/Timetable";
import Teachers from "./pages/Teachers";
import Subjects from "./pages/Subjects";
import { Rooms, Semesters, TimeSlots } from "./pages/Managers";
import Settings from "./pages/Settings";
import Help from "./pages/Help";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "timetable", element: <Timetable /> },
      { path: "teachers", element: <Teachers /> },
      { path: "subjects", element: <Subjects /> },
      { path: "rooms", element: <Rooms /> },
      { path: "semesters", element: <Semesters /> },
      { path: "timeslots", element: <TimeSlots /> },
      { path: "settings", element: <Settings /> },
      { path: "help", element: <Help /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
