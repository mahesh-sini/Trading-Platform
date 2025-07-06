import React from 'react';
import { useRouter } from 'next/router';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { 
  ChartBarIcon, 
  CpuChipIcon, 
  ShieldCheckIcon, 
  LightBulbIcon,
  ClockIcon,
  GlobeAltIcon,
  CurrencyDollarIcon,
  UserGroupIcon,
  ArrowLeftIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';

const Features: React.FC = () => {
  const router = useRouter();

  const features = [
    {
      icon: ChartBarIcon,
      title: 'Advanced Analytics',
      description: 'Professional-grade charts with 50+ technical indicators, real-time market data, and customizable dashboards.',
      details: [
        'Real-time market data from major exchanges',
        '50+ technical indicators and overlays',
        'Customizable chart layouts and timeframes',
        'Advanced drawing tools and annotations'
      ]
    },
    {
      icon: CpuChipIcon,
      title: 'AI-Powered Insights',
      description: 'Machine learning algorithms analyze market patterns and provide predictive analytics for better trading decisions.',
      details: [
        'Price prediction models with 85% accuracy',
        'Sentiment analysis from news and social media',
        'Pattern recognition and trend analysis',
        'Automated signal generation'
      ]
    },
    {
      icon: ShieldCheckIcon,
      title: 'Enterprise Security',
      description: 'Bank-level security with encrypted connections, secure API management, and compliance standards.',
      details: [
        'End-to-end encryption for all data',
        'Two-factor authentication',
        'SOC 2 Type II compliance',
        'Regular security audits and monitoring'
      ]
    },
    {
      icon: LightBulbIcon,
      title: 'Smart Strategies',
      description: 'Automated trading strategies with built-in risk management and portfolio optimization.',
      details: [
        'Pre-built strategy templates',
        'Custom strategy builder',
        'Backtesting with historical data',
        'Risk management and position sizing'
      ]
    },
    {
      icon: ClockIcon,
      title: '24/7 Monitoring',
      description: 'Round-the-clock market monitoring with instant alerts and notifications.',
      details: [
        'Real-time price alerts',
        'Custom notification triggers',
        'Mobile app notifications',
        'Email and SMS alerts'
      ]
    },
    {
      icon: GlobeAltIcon,
      title: 'Global Markets',
      description: 'Access to multiple asset classes and markets worldwide.',
      details: [
        'Stocks, ETFs, options, and crypto',
        'International markets access',
        'Forex and commodities',
        'Real-time global market data'
      ]
    },
    {
      icon: CurrencyDollarIcon,
      title: 'Cost Effective',
      description: 'Competitive pricing with transparent fees and no hidden costs.',
      details: [
        'Low commission rates',
        'No platform fees',
        'Transparent pricing structure',
        'Volume discounts available'
      ]
    },
    {
      icon: UserGroupIcon,
      title: 'Expert Support',
      description: '24/7 customer support from trading experts and technical specialists.',
      details: [
        '24/7 live chat support',
        'Trading education resources',
        'Market research and analysis',
        'Dedicated account managers'
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-secondary-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-2">
              <ChartBarIcon className="w-8 h-8 text-primary-600" />
              <span className="text-xl font-bold text-gray-900">
                AI Trading Platform
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                onClick={() => router.push('/')}
                className="flex items-center"
              >
                <ArrowLeftIcon className="w-4 h-4 mr-2" />
                Back to Home
              </Button>
              <Button
                variant="primary"
                onClick={() => router.push('/auth/register')}
              >
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-20 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-8">
            Powerful Features for
            <br />
            <span className="text-primary-600">Modern Traders</span>
          </h1>
          <p className="text-xl text-gray-600 mb-12 max-w-3xl mx-auto">
            Discover all the tools and features that make our AI trading platform
            the choice of successful traders worldwide.
          </p>
        </div>
      </section>

      {/* Features Grid */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {features.map((feature, index) => (
              <Card key={index} variant="elevated" className="p-6">
                <div className="flex items-start space-x-4">
                  <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <feature.icon className="w-6 h-6 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-gray-600 mb-4">
                      {feature.description}
                    </p>
                    <ul className="space-y-2">
                      {feature.details.map((detail, detailIndex) => (
                        <li key={detailIndex} className="flex items-center text-sm text-gray-600">
                          <div className="w-1.5 h-1.5 bg-primary-500 rounded-full mr-3"></div>
                          {detail}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-primary-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Experience These Features?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join thousands of traders who are already using our platform to maximize their returns.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              size="lg"
              onClick={() => router.push('/auth/register')}
              className="bg-white text-primary-900 hover:bg-gray-100 group"
            >
              Start Free Trial
              <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => router.push('/auth/login')}
              className="border-white text-white hover:bg-white hover:text-primary-900"
            >
              Sign In
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ChartBarIcon className="w-6 h-6" />
              <span className="text-lg font-bold">AI Trading Platform</span>
            </div>
            <div className="text-sm text-gray-400">
              © 2024 AI Trading Platform. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Features;