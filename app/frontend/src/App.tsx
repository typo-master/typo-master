import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "./config";
import { AuthProvider } from "./contexts/AuthContext";
import MainLayout from "./Layout";
import HomePage from "./pages/Home";
import WorkspacePage from "./pages/Workspace";
import SettingsPage from "./pages/Settings";
import IntegrationDocsPage from "./pages/IntegrationDocs";

function App() {
  return (
    <ConfigProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<HomePage />} />
              <Route path="workspace" element={<Navigate to="/workspace/chat" replace />} />
              <Route path="workspace/:tab" element={<WorkspacePage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="docs" element={<IntegrationDocsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  );
}

export default App;
