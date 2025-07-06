import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuthStore } from '@/store/authStore';
import { Order, OrderStatus as OrderStatusEnum } from '@/types';
import { 
  ClockIcon, 
  CheckCircleIcon, 
  XCircleIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

interface OrderStatusProps {
  order: Order;
  className?: string;
}

export const OrderStatus: React.FC<OrderStatusProps> = ({ order, className }) => {
  const [realTimeOrder, setRealTimeOrder] = useState<Order>(order);
  const { user } = useAuthStore();
  const { 
    isConnected, 
    subscribe, 
    unsubscribe, 
    registerMessageHandler,
    unregisterMessageHandler
  } = useWebSocket();

  useEffect(() => {
    if (isConnected && user?.id) {
      // Subscribe to user's order updates
      subscribe(`orders.${user.id}`);
    }

    // Register handler for order updates
    const handleOrderUpdate = (data: any) => {
      if (data.order_id === order.id) {
        setRealTimeOrder(prev => ({
          ...prev,
          status: data.status,
          filled_quantity: data.filled_quantity || prev.filled_quantity,
          average_fill_price: data.average_fill_price || prev.average_fill_price,
          updated_at: data.timestamp || new Date().toISOString()
        }));
      }
    };

    registerMessageHandler('order_update', handleOrderUpdate);

    return () => {
      if (user?.id) {
        unsubscribe(`orders.${user.id}`);
      }
      unregisterMessageHandler('order_update');
    };
  }, [isConnected, user?.id, order.id, subscribe, unsubscribe, registerMessageHandler, unregisterMessageHandler]);

  const getStatusIcon = (status: OrderStatusEnum) => {
    switch (status) {
      case OrderStatusEnum.PENDING:
        return <ClockIcon className="w-5 h-5 text-warning-500" />;
      case OrderStatusEnum.FILLED:
        return <CheckCircleIcon className="w-5 h-5 text-success-500" />;
      case OrderStatusEnum.PARTIALLY_FILLED:
        return <ClockIcon className="w-5 h-5 text-primary-500" />;
      case OrderStatusEnum.CANCELLED:
        return <XCircleIcon className="w-5 h-5 text-gray-500" />;
      case OrderStatusEnum.REJECTED:
        return <ExclamationTriangleIcon className="w-5 h-5 text-danger-500" />;
      default:
        return <ClockIcon className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: OrderStatusEnum) => {
    switch (status) {
      case OrderStatusEnum.PENDING:
        return 'text-warning-600 bg-warning-50 border-warning-200';
      case OrderStatusEnum.FILLED:
        return 'text-success-600 bg-success-50 border-success-200';
      case OrderStatusEnum.PARTIALLY_FILLED:
        return 'text-primary-600 bg-primary-50 border-primary-200';
      case OrderStatusEnum.CANCELLED:
        return 'text-gray-600 bg-gray-50 border-gray-200';
      case OrderStatusEnum.REJECTED:
        return 'text-danger-600 bg-danger-50 border-danger-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const fillPercentage = realTimeOrder.filled_quantity / realTimeOrder.quantity * 100;

  return (
    <Card className={clsx('transition-colors duration-200', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getStatusIcon(realTimeOrder.status as OrderStatusEnum)}
            <span className="font-medium text-gray-900">
              Order #{realTimeOrder.id.slice(-8)}
            </span>
            <div className={clsx(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-success-500' : 'bg-gray-400'
            )} />
          </div>
          <div className={clsx(
            'px-2 py-1 rounded-full text-xs font-medium',
            getStatusColor(realTimeOrder.status as OrderStatusEnum)
          )}>
            {realTimeOrder.status.replace('_', ' ').toUpperCase()}
          </div>
        </div>
      </CardHeader>

      <CardBody>
        <div className="space-y-4">
          {/* Order Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-500">Symbol</div>
              <div className="font-medium">{realTimeOrder.symbol}</div>
            </div>
            <div>
              <div className="text-gray-500">Side</div>
              <div className={clsx(
                'font-medium',
                realTimeOrder.side === 'buy' ? 'text-success-600' : 'text-danger-600'
              )}>
                {realTimeOrder.side.toUpperCase()}
              </div>
            </div>
            <div>
              <div className="text-gray-500">Type</div>
              <div className="font-medium">{realTimeOrder.type.toUpperCase()}</div>
            </div>
            <div>
              <div className="text-gray-500">Quantity</div>
              <div className="font-medium">{realTimeOrder.quantity}</div>
            </div>
          </div>

          {/* Price Information */}
          {realTimeOrder.price && (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-500">Order Price</div>
                <div className="font-medium">${realTimeOrder.price.toFixed(2)}</div>
              </div>
              {realTimeOrder.average_fill_price && (
                <div>
                  <div className="text-gray-500">Avg Fill Price</div>
                  <div className="font-medium">${realTimeOrder.average_fill_price.toFixed(2)}</div>
                </div>
              )}
            </div>
          )}

          {/* Fill Progress */}
          {realTimeOrder.status === OrderStatusEnum.PARTIALLY_FILLED && (
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500">Fill Progress</span>
                <span className="font-medium">
                  {realTimeOrder.filled_quantity} / {realTimeOrder.quantity}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${fillPercentage}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {fillPercentage.toFixed(1)}% filled
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 text-xs text-gray-500">
            <div>
              <div>Created</div>
              <div>{new Date(realTimeOrder.created_at).toLocaleString()}</div>
            </div>
            <div>
              <div>Last Update</div>
              <div>{new Date(realTimeOrder.updated_at).toLocaleString()}</div>
            </div>
          </div>

          {/* Real-time indicator */}
          <div className="flex items-center justify-between text-xs">
            <div className="text-gray-400">
              Status updates in real-time
            </div>
            <div className={clsx(
              'flex items-center space-x-1',
              isConnected ? 'text-success-600' : 'text-gray-400'
            )}>
              <div className={clsx(
                'w-1.5 h-1.5 rounded-full',
                isConnected ? 'bg-success-500 animate-pulse' : 'bg-gray-400'
              )} />
              <span>{isConnected ? 'Live' : 'Offline'}</span>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};