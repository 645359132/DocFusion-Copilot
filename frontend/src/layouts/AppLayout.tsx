import { Outlet } from 'react-router-dom';
import MobileNavBar from '@/components/MobileNavBar';
import NavSidebar from '@/components/NavSidebar';
import TopBar from '@/components/TopBar';
import ToastViewport from '@/components/ToastViewport';
import TraceabilityDrawer from '@/components/TraceabilityDrawer';

export default function AppLayout() {
  return (
    <div className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1600px] gap-6">
        <NavSidebar />
        <div className="relative min-h-[calc(100vh-2rem)] flex-1">
          <div className="space-y-6">
            <TopBar />
            <main className="pb-10">
              <Outlet />
            </main>
          </div>
          <ToastViewport />
          <TraceabilityDrawer />
        </div>
      </div>
      <MobileNavBar />
    </div>
  );
}