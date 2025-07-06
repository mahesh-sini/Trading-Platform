import React from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { BaseComponentProps } from '@/types';

interface LayoutProps extends BaseComponentProps {
  showSidebar?: boolean;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  showSidebar = true,
  className,
}) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="flex pt-20"> {/* Add top padding to account for fixed header */}
        {showSidebar && <Sidebar />}
        <main className={`flex-1 ${showSidebar ? 'ml-64' : ''} ${className || ''}`}>
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};