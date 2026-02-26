#!/usr/bin/env python3
"""
Platinum Engine Test - 5 Verification Samples
============================================
Generates 5 samples from core and alarmo files to validate:
- Resilient thought extraction
- Chunking by full classes
- Smart LDI calibration
- Anti-rudeness system prompt
- AST robustness

Output: data/synthetic/platinum_test_5samples.jsonl
"""

import sys
import json
import logging
from pathlib import Path

# Importar motor validado
sys.path.insert(0, str(Path(__file__).parent))
from generate_gold_injection_dataset import process_file

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_platinum_5samples():
    """Generate 5 samples from core and alarmo for validation."""
    
    # Target files (2 core, 2 alarmo, 1 large core)
    # Paths are relative; ensure the example files exist under data/raw/ before running this test.
    # Change or extend this list to suit your own domain’s raw inputs.
    test_files = [
        "data/raw/alarmo_tests_common.txt",
        "data/raw/home-assistant-core_home-assistant-core_account.txt",
        "data/raw/home-assistant-core_home-assistant-core_active_update_coordinator.txt",
    ]
    
    output_file = Path("data/synthetic/platinum_test_5samples.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Clear output file
    with open(output_file, 'w', encoding='utf-8') as f:
        pass
    
    logger.info("🔬 TEST PLATINUM - 5 SAMPLES")
    logger.info(f"   Files: {len(test_files)}")
    logger.info(f"   Salida: {output_file}")
    logger.info("=" * 80)
    
    total_samples = 0
    results = []
    
    for file_path_str in test_files:
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            logger.warning(f"⚠️  Archivo no encontrado: {file_path}")
            continue
        
        logger.info(f"\n📂 Procesando: {file_path.name}")
        
        try:
            samples = process_file(file_path)
            
            if samples:
                # Save samples
                with open(output_file, 'a', encoding='utf-8') as f:
                    for sample in samples:
                        f.write(json.dumps(sample, ensure_ascii=False) + '\n')
                
                total_samples += len(samples)
                
                # Analyze quality
                    for i, sample in enumerate(samples[:3]):  # First 3 of each file
                    conv = sample.get('conversation', [])
                    
                    # Extract assistant reasoning
                    reasoning = ""
                    code = ""
                    ldi = sample.get('metadata', {}).get('ldi_3_3', 0)
                    
                    for msg in conv:
                        if msg.get('role') == 'assistant':
                            content = msg.get('content', '')
                            # Extract <think>
                            if '<think>' in content:
                                think_start = content.find('<think>') + 7
                                think_end = content.find('</think>')
                                if think_end != -1:
                                    reasoning = content[think_start:think_end].strip()
                            # Extract code from tool_call
                            if '<tool_call>' in content:
                                tool_start = content.find('<tool_call>') + 11
                                tool_end = content.find('</tool_call>')
                                if tool_end != -1:
                                    try:
                                        tool_json = json.loads(content[tool_start:tool_end])
                                        code = tool_json.get('arguments', {}).get('content', '')
                                    except:
                                        pass
                    
                    results.append({
                        'file': file_path.name,
                        'sample': i + 1,
                        'ldi': ldi,
                        'reasoning_len': len(reasoning),
                        'code_len': len(code),
                        'reasoning_preview': reasoning[:200] + '...' if len(reasoning) > 200 else reasoning
                    })
                
                logger.info(f"   ✅ {len(samples)} samples generated")
            else:
                logger.warning(f"   ⚠️  Sin muestras válidas")
        
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            continue
    
    # REPORTE FINAL
    logger.info("\n" + "=" * 80)
    logger.info(f"✅ TEST COMPLETED")
    logger.info(f"   Total samples: {total_samples}")
    logger.info(f"   Output: {output_file}")
    logger.info("=" * 80)
    
    # Mostrar análisis de calidad
    logger.info("\n📊 QUALITY ANALYSIS:")
    for r in results:
        logger.info(f"\n{r['file']} - Sample {r['sample']}:")
        logger.info(f"  LDI 3.3: {r['ldi']:.2f}")
        logger.info(f"  Reasoning: {r['reasoning_len']} chars")
        logger.info(f"  Code: {r['code_len']} chars")
        logger.info(f"  Preview: {r['reasoning_preview']}")
    
    # Calcular yield
    if results:
        avg_ldi = sum(r['ldi'] for r in results) / len(results)
        logger.info(f"\n📈 METRICS:")
        logger.info(f"   LDI Promedio: {avg_ldi:.2f}")
        logger.info(f"   Yield: {total_samples} samples from {len(test_files)} files")


if __name__ == "__main__":
    test_platinum_5samples()
