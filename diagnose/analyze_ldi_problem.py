#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
LDI Filter Problem Analysis
===========================
Identifies false negatives: samples with deep reasoning (>1000 chars)
but LDI < 2.5 that were discarded.

CONCLUSION:
The current LDI penalizes long reasoning inside <think>, whereas it should
measure logic density only within the tool_call.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Datasets
GOLD_PATH = Path("data/synthetic/hacs_gold_dataset.jsonl")
PLATINUM_PATH = Path("data/curated/hacs_platinum_dataset.jsonl")


class LDIAnalyzer:
    """Logic Density Index analyzer identical to the one used in curation"""
    
    PROGRAMMING_KEYWORDS = {
        'def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 'for', 
        'while', 'try', 'except', 'async', 'await', 'self', 'None', 'True', 
        'False', 'dict', 'list', 'str', 'int', 'float', 'bool', '__init__', 
        'lambda', 'yield', 'with', 'as', 'raise', 'assert', 'pass', 'break', 
        'continue', 'and', 'or', 'not', 'in', 'is', 'config', 'state', 'hass',
        'entity', 'device', 'sensor', 'binary_sensor', 'switch', 'light', 'climate'
    }
    
    CODE_SYMBOLS = r'[\[\]{}()=<>+\-*/%&|^~!:;,.@#$]'
    
    @staticmethod
    def count_code_tokens(text: str) -> int:
        """Count code tokens: JSON, backticks, keywords, symbols"""
        code_tokens = 0
        
        # JSON blocks
        json_blocks = re.findall(r'\{[^}]*\}', text)
        for block in json_blocks:
            code_tokens += len(block.split())
        
        # Triple backticks
        code_blocks = re.findall(r'```[\s\S]*?```', text)
        for block in code_blocks:
            code_tokens += len(block.split())
        
        # Programming keywords
        words = text.lower().split()
        code_tokens += sum(1 for word in words if word in LDIAnalyzer.PROGRAMMING_KEYWORDS)
        
        # Symbols
        code_tokens += len(re.findall(LDIAnalyzer.CODE_SYMBOLS, text))
        
        return code_tokens
    
    @staticmethod
    def count_natural_language_tokens(text: str) -> int:
        """Count natural language tokens (excluding technical terms)"""
        # Remove code blocks
        clean_text = re.sub(r'```[\s\S]*?```', '', text)
        clean_text = re.sub(r'\{[^}]*\}', '', clean_text)
        
        # Count words
        words = clean_text.split()
        natural_tokens = sum(
            1 for word in words 
            if word.lower() not in LDIAnalyzer.PROGRAMMING_KEYWORDS
            and not re.match(r'^[\[\]{}()=<>+\-*/%&|^~!:;,.@#$]+$', word)
        )
        
        return max(natural_tokens, 1)  # Avoid division by zero
    
    @staticmethod
    def calculate_ldi(text: str) -> Tuple[float, int, int]:
        """Calculate Logic Density Index as the code/natural ratio"""
        code_tokens = LDIAnalyzer.count_code_tokens(text)
        natural_tokens = LDIAnalyzer.count_natural_language_tokens(text)
        ldi = code_tokens / natural_tokens
        return ldi, code_tokens, natural_tokens


def load_datasets() -> Tuple[List[Dict], List[Dict]]:
    """Load both datasets"""
    print("📂 Cargando datasets...")
    
    with open(GOLD_PATH) as f:
        gold = [json.loads(line) for line in f]
    
    with open(PLATINUM_PATH) as f:
        platinum = [json.loads(line) for line in f]
    
    print(f"   ✅ Gold: {len(gold)} muestras")
    print(f"   ✅ Platinum: {len(platinum)} muestras")
    
    return gold, platinum


def analyze_false_negatives(gold: List[Dict], platinum: List[Dict]) -> None:
    """
    Identifica muestras con razonamiento profundo que fueron descartadas.
    
    FALSO NEGATIVO: 
    - Think block >1000 caracteres (razonamiento profundo PEDIDO)
    - LDI <2.5 (descartado)
    - NO está en Platinum
    """
    print("\n" + "="*80)
    print("🔬 ANÁLISIS DEL PROBLEMA LDI - FALSOS NEGATIVOS")
    print("="*80)
    
    # Platinum IDs
    platinum_ids = {sample['id'] for sample in platinum}
    
    # Search for false negatives
    false_negatives = []
    
    for sample in gold:
        if sample['id'] not in platinum_ids:
            # Extract turn 2 (assistant response with <think>)
            turns = sample['conversation']  # Key is 'conversation', not 'conversations'
            turn2 = next((t['content'] for t in turns if t['role'] == 'assistant'), '')
            
            # Extract <think> block
            think_match = re.search(r'<think>(.*?)</think>', turn2, re.DOTALL)
            if not think_match:
                continue
            
            think_block = think_match.group(1).strip()
            think_length = len(think_block)
            
            # Solo considerar muestras con razonamiento profundo
            if think_length > 1000:
                # Calculate LDI
                ldi, code_tokens, natural_tokens = LDIAnalyzer.calculate_ldi(turn2)
                
                # Si LDI <2.5, es un falso negativo
                if ldi < 2.5:
                    # Extract instruction (turn 1)
                    instruction = turns[0]['content']
                    instruction_preview = instruction[:80] + "..." if len(instruction) > 80 else instruction
                    
                    false_negatives.append({
                        'id': sample['id'],
                        'instruction': instruction_preview,
                        'think_length': think_length,
                        'ldi': round(ldi, 2),
                        'code_tokens': code_tokens,
                        'natural_tokens': natural_tokens
                    })
    
    print(f"📊 Muestras descartadas con razonamiento >1000 chars: {len(false_negatives)}")
    print(f"\nEJEMPLOS DE FALSOS NEGATIVOS (primeros 10):\n")
    
    for i, fn in enumerate(false_negatives[:10], 1):
        print(f"{i}. ID: {fn['id']}")
        print(f"   Instrucción: {fn['instruction']}")
        print(f"   Think Length: {fn['think_length']} chars")
        print(f"   LDI: {fn['ldi']} (código: {fn['code_tokens']}, texto: {fn['natural_tokens']})")
        print(f"   ⚠️  DESCARTADO por LDI < 2.5 a pesar del razonamiento profundo\n")
    
    print("="*80)
    print("💡 CONCLUSIÓN:")
    print("   El filtro LDI actual PENALIZA el razonamiento profundo que pedimos.")
    print("   Propuesta: LDI 3.0 debe medir densidad solo en el tool_call, no en <think>")
    print("="*80)
    
    # Estadísticas adicionales
    avg_think = sum(fn['think_length'] for fn in false_negatives) / len(false_negatives)
    avg_ldi = sum(fn['ldi'] for fn in false_negatives) / len(false_negatives)
    
    print(f"\n📈 ESTADÍSTICAS DE FALSOS NEGATIVOS:")
    print(f"   - Total: {len(false_negatives)} muestras")
    print(f"   - Promedio Think Length: {avg_think:.0f} chars")
    print(f"   - Promedio LDI: {avg_ldi:.2f}")
    print(f"   - Porcentaje del Gold: {100 * len(false_negatives) / len(gold):.1f}%")
    print(f"   - Tasa de retención actual: {100 * len(platinum) / len(gold):.1f}%")
    print(f"   - Tasa potencial con LDI 3.0: {100 * (len(platinum) + len(false_negatives)) / len(gold):.1f}%")


def main():
    print("="*80)
    print("ANÁLISIS DEL PROBLEMA DEL FILTRO LDI")
    print("="*80)
    print("🎯 Objetivo: Identificar el problema con el filtro LDI actual\n")
    
    # Load datasets
    gold, platinum = load_datasets()
    
    # Analyze false negatives
    analyze_false_negatives(gold, platinum)


if __name__ == "__main__":
    main()
