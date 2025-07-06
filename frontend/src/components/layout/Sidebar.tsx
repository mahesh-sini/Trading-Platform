import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { clsx } from 'clsx';
import {
  HomeIcon,
  ChartBarIcon,
  BanknotesIcon,
  CpuChipIcon,
  NewspaperIcon,
  EyeIcon,
  CogIcon,
  DocumentChartBarIcon,
  PlayIcon,
} from '@heroicons/react/24/outline';
import { NavigationItem } from '@/types';

const navigation: NavigationItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Portfolio', href: '/portfolio', icon: ChartBarIcon },
  { name: 'Trading', href: '/trading', icon: BanknotesIcon },
  { name: 'Auto Trading', href: '/auto-trading', icon: PlayIcon },
  { name: 'AI Insights', href: '/ai-insights', icon: CpuChipIcon },
  { name: 'Market Data', href: '/market-data', icon: DocumentChartBarIcon },
  { name: 'News', href: '/news', icon: NewspaperIcon },
  { name: 'Watchlists', href: '/watchlists', icon: EyeIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
];

export const Sidebar: React.FC = () => {
  const router = useRouter();

  return (
    <div className="fixed inset-y-0 left-0 z-40 w-64 bg-white shadow-lg border-r border-gray-200 pt-16">
      <div className="flex flex-col h-full">
        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-2">
          {navigation.map((item) => {
            const isActive = router.pathname === item.href;
            const Icon = item.icon;
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={clsx(
                  'flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700 border-r-2 border-primary-600'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                )}
              >
                {Icon && (
                  <Icon
                    className={clsx(
                      'w-5 h-5 mr-3',
                      isActive ? 'text-primary-600' : 'text-gray-400'
                    )}
                  />
                )}
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div className="px-4 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm text-gray-600">Market Open</span>
            </div>
            <div className="text-xs text-gray-500">
              {new Date().toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};