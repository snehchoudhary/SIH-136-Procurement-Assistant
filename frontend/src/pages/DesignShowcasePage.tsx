import React from 'react';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { StatusChip } from '../components/ui/StatusChip';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Search, Mail } from 'lucide-react';

export default function DesignShowcasePage() {
  return (
    <div className='p-6 max-w-6xl mx-auto flex gap-10 fade-in'>
      <div className='w-48 shrink-0 hidden md:block'>
        <div className='sticky top-24 space-y-2'>
          <h3 className='font-semibold text-sm uppercase tracking-wider text-muted mb-4'>Components</h3>
          {['Buttons', 'Badges & Chips', 'Inputs', 'Cards'].map(item => (
            <a key={item} href={`#${item.toLowerCase().replace(/ /g, '-')}`} className='block text-sm text-muted hover:text-primary py-1 transition-colors'>
              {item}
            </a>
          ))}
        </div>
      </div>
      
      <div className='flex-1 space-y-16 pb-20'>
        <PageHeader title='Design Showcase' description='A collection of all UI components used in PilotProof.' />
        
        <section id='buttons' className='space-y-6'>
          <div className='border-b border-border pb-2'>
            <h2 className='text-2xl font-heading font-semibold'>Buttons</h2>
          </div>
          <Card className='p-8 flex flex-wrap gap-4 items-center'>
            <Button>Default</Button>
            <Button variant='primary'>Primary</Button>
            <Button variant='outline'>Outline</Button>
            <Button variant='ghost'>Ghost</Button>
            <Button variant='danger'>Danger</Button>
            <Button isLoading>Loading</Button>
            <Button leftIcon={<Mail size={16} />}>With Icon</Button>
          </Card>
        </section>

        <section id='badges-&-chips' className='space-y-6'>
          <div className='border-b border-border pb-2'>
            <h2 className='text-2xl font-heading font-semibold'>Badges & Status Chips</h2>
          </div>
          <Card className='p-8 flex flex-wrap gap-4 items-center'>
            <Badge>Default</Badge>
            <Badge variant='success'>Success</Badge>
            <Badge variant='warning'>Warning</Badge>
            <Badge variant='error'>Error</Badge>
            <Badge variant='info'>Info</Badge>
            
            <div className='w-px h-6 bg-border mx-4'></div>
            
            <StatusChip status='Verified' />
            <StatusChip status='Pending' />
            <StatusChip status='Disputed' />
            <StatusChip status='Needs Verification' />
            <StatusChip status='AI-Drafted' />
          </Card>
        </section>

        <section id='inputs' className='space-y-6'>
          <div className='border-b border-border pb-2'>
            <h2 className='text-2xl font-heading font-semibold'>Inputs</h2>
          </div>
          <Card className='p-8 grid md:grid-cols-2 gap-6'>
            <Input label='Standard Input' placeholder='Type here...' />
            <Input label='With Icon' leftSlot={<Search size={16} />} placeholder='Search...' />
            <Input label='Error State' error helperText='This field is required.' defaultValue='Invalid value' />
            <Input label='Success State' success helperText='Looks good!' defaultValue='Valid value' />
          </Card>
        </section>
        
        <section id='cards' className='space-y-6'>
          <div className='border-b border-border pb-2'>
            <h2 className='text-2xl font-heading font-semibold'>Cards</h2>
          </div>
          <div className='grid md:grid-cols-2 gap-6'>
            <Card className='p-6'>
              <h3 className='font-semibold mb-2'>Default Card</h3>
              <p className='text-muted text-sm'>Standard surface card with border.</p>
            </Card>
            <Card elevated className='p-6'>
              <h3 className='font-semibold mb-2'>Elevated Card</h3>
              <p className='text-muted text-sm'>Card with shadow and raised background.</p>
            </Card>
            <Card glow className='p-6 md:col-span-2'>
              <h3 className='font-semibold mb-2'>Glow Card</h3>
              <p className='text-muted text-sm'>Card with custom primary glow hover effect.</p>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}
