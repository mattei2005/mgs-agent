// Canonical monthly network specification, shared with the Python calculation bridge.
import {readFileSync} from 'node:fs';
export const networkRules=JSON.parse(readFileSync(new URL('./network-rules.json',import.meta.url),'utf8'));
export const networks=networkRules.networks;
export const canonicalNetwork=value=>networkRules.legacy_aliases[value]||value;
export function seedNetwork(site){return networkRules.explicit_sites[site.name]||canonicalNetwork(site.network||site.partner);}
export function validateNetwork(value){if(!Object.hasOwn(networks,value))throw Object.assign(Error('Selecione a rede do site'),{status:400});return value;}
